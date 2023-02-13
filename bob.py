import json
import base64
import qrcode
import requests
import asyncio
import datetime
import uuid
import time
import matplotlib.pyplot as plt
from pprint import pprint
from pymongo import MongoClient
from typing import Optional, List
from didcomm.common.types import DID, VerificationMethodType, VerificationMaterial, VerificationMaterialFormat
from didcomm.did_doc.did_doc import DIDDoc, VerificationMethod
from didcomm.did_doc.did_resolver import DIDResolver
from didcomm.message import Message, Attachment, AttachmentDataJson
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



async def main(alice_did, message):
    
    alice_did_doc = json.loads(peer_did.resolve_peer_did(alice_did))
    mediator_did = alice_did_doc["service"][0]["serviceEndpoint"][0]["uri"]
    mediator_did_doc = json.loads(peer_did.resolve_peer_did(mediator_did))
    mediator_endpoint = mediator_did_doc["service"][0]["serviceEndpoint"]
    bob_did_to_alice = await create_peer_did(1,1 )
    bob_basic_message = Message(
        id = str(uuid.uuid4()),
        type="https://didcomm.org/basicmessage/2.0/message",
        body={"content": message},
        created_time= int(datetime.datetime.now().timestamp())            
    )
    bob_basic_message_packed = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = secrets_resolver,
            did_resolver = DIDResolverPeerDID()
        ),
        message = bob_basic_message,
        frm = bob_did_to_alice,
        to = alice_did,
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
    )
    bob_did_to_mediator = await create_peer_did(1,1, service_endpoint="https://www.example.com/bob")
    bob_routed_message = Message(
        id = str(uuid.uuid4()),
        type="https://didcomm.org/routing/2.0/forward",
        body={"next": alice_did},
        to=[mediator_did],
        attachments=[Attachment(
                data=AttachmentDataJson(json=json.loads(bob_basic_message_packed.packed_msg))
            )]
    )

    bob_routed_message_packed = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = secrets_resolver,
            did_resolver = DIDResolverPeerDID()
        ),
        message = bob_routed_message,
        frm = bob_did_to_mediator,
        to = mediator_did,
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
    )
    alice_did_doc = json.loads(peer_did.resolve_peer_did(alice_did))
    mediator_did = alice_did_doc["service"][0]["serviceEndpoint"][0]["uri"]
    #mediator_did = alice_did_doc["service"][0]["serviceEndpoint"][]
    print(mediator_did)

    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    resp = requests.post(mediator_endpoint, headers=headers, json = json.loads(bob_routed_message_packed.packed_msg))
    print("MESSAGE SENT", alice_did, message)

import sys

#check how many arguments were passed
if len(sys.argv) < 3:
    asyncio.run(main(sys.argv[1], "OWF demo"))

else:
    asyncio.run(main(sys.argv[1], sys.argv[2]))
