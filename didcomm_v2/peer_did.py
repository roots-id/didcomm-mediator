""" Peer DID helpers"""
import json
from typing import Optional, List
from didcomm.secrets.secrets_util import generate_x25519_keys_as_jwk_dict, generate_ed25519_keys_as_jwk_dict, jwk_to_secret
from didcomm.did_doc.did_doc import DIDDoc, VerificationMethod, DIDCommService
from didcomm.common.types import DID, DID_URL, VerificationMethodType, VerificationMaterial, VerificationMaterialFormat
from didcomm.did_doc.did_resolver import DIDResolver
from didcomm.secrets.secrets_resolver_editable import SecretsResolverEditable
from didcomm.secrets.secrets_resolver import Secret
from peerdid.core.did_doc_types import DIDCommServicePeerDID
from peerdid import peer_did
from peerdid.did_doc import DIDDocPeerDID
from peerdid.types import VerificationMaterialAuthentication, VerificationMethodTypeAuthentication, VerificationMaterialAgreement, VerificationMethodTypeAgreement, VerificationMaterialFormatPeerDID
from pymongo import MongoClient

class SecretsResolverMongo(SecretsResolverEditable):
    """ Secret Resolver on MongoDB"""
    def __init__(self, mongo_db_uri="mongodb://localhost:27017"):
        self.mongo = MongoClient(mongo_db_uri)
        self.db = self.mongo.mediator
        self.secrets = self.db.secrets

    async def add_key(self, secret: Secret):
        self.secrets.insert_one({
            "kid": secret.kid,
            "type": secret.type.value,
            "verification_material": {
                "format": secret.verification_material.format.value,
                "value": secret.verification_material.value
            }
        })

    async def get_kids(self) -> List[str]:
        kids = self.secrets.find({},{"kid": 1})
        return [k["kid"] for k in kids]
    async def get_key(self, kid: DID_URL) -> Optional[Secret]:
        try:
            key = self.secrets.find({"kid": kid})[0]
            return Secret(
                kid,
                VerificationMethodType(key["type"]),
                VerificationMaterial(VerificationMaterialFormat(
                        key["verification_material"]["format"]),
                        key["verification_material"]["value"]
                        )
                )
        except IndexError:
            return None

    async def get_keys(self, kids: List[DID_URL]) -> List[DID_URL]:
        kids_db = self.secrets.find({"kid": { "$in": kids }},{"kid": 1})
        return [k["kid"] for k in kids_db]

class DIDResolverPeerDID(DIDResolver):
    """ Helper class to resolve Peer DID Documents """
    async def resolve(self, did: DID) -> DIDDoc:
        did_doc_json = peer_did.resolve_peer_did(
            did, format=VerificationMaterialFormatPeerDID.JWK)
        did_doc = DIDDocPeerDID.from_json(did_doc_json)

        return DIDDoc(
            did=did_doc.did,
            key_agreement_kids=did_doc.agreement_kids,
            authentication_kids=did_doc.auth_kids,
            verification_methods=[
                VerificationMethod(
                    id=m.id,
                    type=VerificationMethodType.JSON_WEB_KEY_2020,
                    controller=m.controller,
                    verification_material=VerificationMaterial(
                        format=VerificationMaterialFormat.JWK,
                        value=json.dumps(m.ver_material.value)
                    )
                )
                for m in did_doc.authentication + did_doc.key_agreement
            ],
            didcomm_services=[
                DIDCommService(
                    id=s.id,
                    service_endpoint=s.service_endpoint,
                    routing_keys=s.routing_keys,
                    accept=s.accept
                )
                for s in did_doc.service
                if isinstance(s, DIDCommServicePeerDID)
            ] if did_doc.service else []
        )


async def create_peer_did(self,
                          auth_keys_count: int = 1,
                          agreement_keys_count: int = 1,
                          service_endpoint: Optional[str] = None,
                          service_routing_keys: Optional[List[str]] = None
                          ) -> str:
    """ Helper function to create a Peer DID """
    # 1. generate keys in JWK format
    agreem_keys = [generate_x25519_keys_as_jwk_dict()
                   for _ in range(agreement_keys_count)]
    auth_keys = [generate_ed25519_keys_as_jwk_dict()
                 for _ in range(auth_keys_count)]

    # 2. prepare the keys for peer DID lib
    agreem_keys_peer_did = [
        VerificationMaterialAgreement(
            type=VerificationMethodTypeAgreement.JSON_WEB_KEY_2020,
            format=VerificationMaterialFormatPeerDID.JWK,
            value=k[1],
        )
        for k in agreem_keys
    ]
    auth_keys_peer_did = [
        VerificationMaterialAuthentication(
            type=VerificationMethodTypeAuthentication.JSON_WEB_KEY_2020,
            format=VerificationMaterialFormatPeerDID.JWK,
            value=k[1],
        )
        for k in auth_keys
    ]

    # 3. generate service
    service = None
    if service_endpoint:
        service = json.dumps(
            DIDCommServicePeerDID(
                id="new-id",
                service_endpoint=service_endpoint, routing_keys=service_routing_keys,
                accept=["didcomm/v2"]
            ).to_dict()
        )

    # 4. call peer DID lib
    # if we have just one key (auth), then use numalg0 algorithm
    # otherwise use numalg2 algorithm
    if len(auth_keys_peer_did) == 1 and not agreem_keys_peer_did and not service:
        did = peer_did.create_peer_did_numalgo_0(auth_keys_peer_did[0])
    else:
        did = peer_did.create_peer_did_numalgo_2(
            encryption_keys=agreem_keys_peer_did,
            signing_keys=auth_keys_peer_did,
            service=service,
        )

    # 5. set KIDs as in DID DOC for secrets and store the secret in the secrets resolver
    did_doc = DIDDocPeerDID.from_json(peer_did.resolve_peer_did(did))
    for auth_key, kid in zip(auth_keys, did_doc.auth_kids):
        private_key = auth_key[0]
        private_key["kid"] = kid
        await secrets_resolver.add_key(jwk_to_secret(private_key))

    for agreem_key, kid in zip(agreem_keys, did_doc.agreement_kids):
        private_key = agreem_key[0]
        private_key["kid"] = kid
        await secrets_resolver.add_key(jwk_to_secret(private_key))

    return did

secrets_resolver = SecretsResolverMongo()

def get_secret_resolver():
    """ Secret Resolver singleton"""
    return secrets_resolver
