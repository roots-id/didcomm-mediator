import json
import base64
import qrcode
import requests
import asyncio
import datetime
import uuid
import matplotlib.pyplot as plt
from pprint import pprint
from pymongo import MongoClient
from typing import Optional, List
from didcomm.common.types import DID, VerificationMethodType, VerificationMaterial, VerificationMaterialFormat
from didcomm.did_doc.did_doc import DIDDoc, VerificationMethod
from didcomm.did_doc.did_resolver import DIDResolver
from didcomm.message import Message, FromPrior
from didcomm.secrets.secrets_resolver_demo import SecretsResolverDemo
from didcomm.unpack import unpack, UnpackResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from peerdid.core.did_doc_types import DIDCommServicePeerDID
from didcomm.secrets.secrets_util import generate_x25519_keys_as_jwk_dict, generate_ed25519_keys_as_jwk_dict, jwk_to_secret
from peerdid import peer_did
from peerdid.did_doc import DIDDocPeerDID
from peerdid.types import VerificationMaterialAuthentication, VerificationMethodTypeAuthentication, VerificationMaterialAgreement, VerificationMethodTypeAgreement, VerificationMaterialFormatPeerDID
secrets_resolver = SecretsResolverDemo()

class DIDResolverPeerDID(DIDResolver):
    async def resolve(self, did: DID) -> DIDDoc:
        did_doc_json = peer_did.resolve_peer_did(did, format = VerificationMaterialFormatPeerDID.JWK)
        did_doc = DIDDocPeerDID.from_json(did_doc_json)

        return DIDDoc(
            did=did_doc.did,
            key_agreement_kids = did_doc.agreement_kids,
            authentication_kids = did_doc.auth_kids,
            verification_methods = [
                VerificationMethod(
                    id = m.id,
                    type = VerificationMethodType.JSON_WEB_KEY_2020,
                    controller = m.controller,
                    verification_material = VerificationMaterial(
                        format = VerificationMaterialFormat.JWK,
                        value = json.dumps(m.ver_material.value)
                    )
                )
                for m in did_doc.authentication + did_doc.key_agreement
            ],
             didcomm_services = []
        )

async def create_peer_did(self,
                        auth_keys_count: int = 1,
                        agreement_keys_count: int = 1,
                        service_endpoint: Optional[str] = None,
                        service_routing_keys: Optional[List[str]] = None
                        ) -> str:
        # 1. generate keys in JWK format
        agreem_keys = [generate_x25519_keys_as_jwk_dict() for _ in range(agreement_keys_count)]
        auth_keys = [generate_ed25519_keys_as_jwk_dict() for _ in range(auth_keys_count)]

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


async def ping_endpoint(mediator_url):
    oob_url = requests.get(mediator_url).text
    received_msg_encoded = oob_url.split("=")[1]
    received_msg_decoded = json.loads(str(base64.urlsafe_b64decode(received_msg_encoded + "=="), "utf-8"))
    alice_did_for_mediator = await create_peer_did(1,1)
    print("OOB invitation message:")
    pprint(received_msg_decoded)

    ping_msg = Message(
        body = { "response_requested": True },
        id = str(uuid.uuid4()),
        type = "https://didcomm.org/trust-ping/2.0/ping",
        frm = alice_did_for_mediator,
        to = [received_msg_decoded["from"]]
    )
    print()
    print()
    print("############ Create DIDCOMM Message")
    pprint(ping_msg.as_dict())

    alice_trust_ping_packed = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = secrets_resolver,
            did_resolver = DIDResolverPeerDID()
        ),
        message = ping_msg,
        frm = alice_did_for_mediator,
        to = received_msg_decoded["from"],
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
    )
    print()
    print()
    print("############Packed message:")
    pprint(json.loads(alice_trust_ping_packed.packed_msg))
    trust_ping_did_doc = json.loads(peer_did.resolve_peer_did(received_msg_decoded["from"]))
    trust_ping_endpoint = trust_ping_did_doc["service"][0]["serviceEndpoint"]
    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    print()
    print()
    print("############Sending packed message to mediator:", mediator_url)
    resp = requests.post(trust_ping_endpoint, headers=headers, json = json.loads(alice_trust_ping_packed.packed_msg))

    print()
    print()
    print("############Response packed from mediator:")
    pprint(resp.json())
    trust_ping_response = await unpack(
        resolvers_config=ResolversConfig(
            secrets_resolver=secrets_resolver,
            did_resolver=DIDResolverPeerDID()
        ),
        packed_msg= resp.json()
    )
    #print 2 new lines
    print()
    print()
    print("############Response unpacked from mediator:")
    print(trust_ping_response.message.as_dict())

    print()
    print()
    print("############Succesful trust ping for mediator", mediator_url)
    print(trust_ping_response.message.type)



mediator_url = "https://mediator.rootsid.cloud/oob_url"
asyncio.run(ping_endpoint(mediator_url))