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



async def main():
    oob_url = requests.get("https://mediator.rootsid.cloud/oob_url").text
    received_msg_encoded = oob_url.split("=")[1]
    received_msg_decoded = json.loads(str(base64.urlsafe_b64decode(received_msg_encoded + "=="), "utf-8"))
    pprint(received_msg_decoded)
    alice_did_for_mediator = await create_peer_did(1,1)
    alice_mediate_grant = Message(
        custom_headers = [{"return_route": "all"}],
        id = str(uuid.uuid4()),
        type = "https://didcomm.org/coordinate-mediation/2.0/mediate-request",
        body = {}
    )

    alice_mediate_grant_packed = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = secrets_resolver,
            did_resolver = DIDResolverPeerDID()
        ),
        message = alice_mediate_grant,
        frm = alice_did_for_mediator,
        to = received_msg_decoded["from"],
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
        )


    mediator_did_doc = json.loads(peer_did.resolve_peer_did(received_msg_decoded["from"]))
    mediator_endpoint = mediator_did_doc["service"][0]["serviceEndpoint"]
    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    resp = requests.post(mediator_endpoint, headers=headers, json = json.loads(alice_mediate_grant_packed.packed_msg))
    mediator_unpack_msg = await unpack(
        resolvers_config=ResolversConfig(
            secrets_resolver=secrets_resolver,
            did_resolver=DIDResolverPeerDID()
        ),
        packed_msg= resp.json()
    )

    # mediator rotated did
    mediator_routing_key = mediator_unpack_msg.message.body["routing_did"]
    mediator_did = mediator_unpack_msg.message.from_prior.sub

    #alice_did_new = await create_peer_did(1, 1, service_endpoint=mediator_endpoint, service_routing_keys=[mediator_routing_key])
    alice_did_for_bob = await create_peer_did(1, 1, service_endpoint=[{"uri": mediator_routing_key}])

    print("*****************Alice's DID for Bob:")
    print(alice_did_for_bob)
    alice_keylist_update = Message(
        id = "unique-id-293e9a922efff",
        type = "https://didcomm.org/coordinate-mediation/2.0/keylist-update",
        body = {
            "updates":[
            {
                "recipient_did": alice_did_for_bob,
                "action": "add"
            }
        ]
        }
    )
    alice_keylist_update_packed_msg = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = secrets_resolver,
            did_resolver = DIDResolverPeerDID()
        ),
        message = alice_keylist_update,
        frm = alice_did_for_mediator,
        to = mediator_did,
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
    )
    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    resp = requests.post(mediator_endpoint, headers=headers, data = alice_keylist_update_packed_msg.packed_msg)
    mediator_unpack_msg2 = await unpack(
        resolvers_config=ResolversConfig(
            secrets_resolver=secrets_resolver,
            did_resolver=DIDResolverPeerDID()
        ),
        packed_msg= resp.json()
    )
    print("******SHARE***********Alice's DID for Bob:")

    while True:
        alice_status_check = Message(
            id = "unique-id-293e9a922efffxxx",
            type = "https://didcomm.org/messagepickup/3.0/status-request",
            body = {}
        )

        alice_status_check_packed_msg = await pack_encrypted(
            resolvers_config = ResolversConfig(
                secrets_resolver = secrets_resolver,
                did_resolver = DIDResolverPeerDID()
            ),
            message = alice_status_check,
            to = mediator_did,
            frm = alice_did_for_mediator,
            sign_frm = None,
            pack_config = PackEncryptedConfig(protect_sender_id=False)
        )
        headers = {"Content-Type": "application/didcomm-encrypted+json"}
        resp3 = requests.post(mediator_endpoint, headers=headers, data = alice_status_check_packed_msg.packed_msg)

        mediator_unpack_status = await unpack(
            resolvers_config=ResolversConfig(
                secrets_resolver=secrets_resolver,
                did_resolver=DIDResolverPeerDID()
            ),
            packed_msg= resp3.json()
        )
        print("Messages in Mediator queue: " + str(mediator_unpack_status.message.body["message_count"]))
        if mediator_unpack_status.message.body["message_count"] > 0:
            
            alice_delivery_request = Message(
                id = "unique-id-293e9a922efffxxxff",
                type = "https://didcomm.org/messagepickup/3.0/delivery-request",
                body = {"limit": 1}
            )

            alice_delivery_request_packed_msg = await pack_encrypted(
                resolvers_config = ResolversConfig(
                    secrets_resolver = secrets_resolver,
                    did_resolver = DIDResolverPeerDID()
                ),
                message = alice_delivery_request,
                to = mediator_did,
                frm = alice_did_for_mediator,
                sign_frm = None,
                pack_config = PackEncryptedConfig(protect_sender_id=False)
            )
            headers = {"Content-Type": "application/didcomm-encrypted+json"}
            resp4 = requests.post(mediator_endpoint, headers=headers, data = alice_delivery_request_packed_msg.packed_msg)

            mediator_delivery = await unpack(
                resolvers_config=ResolversConfig(
                    secrets_resolver=secrets_resolver,
                    did_resolver=DIDResolverPeerDID()
                ),
                packed_msg= resp4.json()
            )
            bob_packed_msg = mediator_delivery.message.attachments[0].data.json
            msg_id = mediator_delivery.message.attachments[0].id

            bob_msg = await unpack(
                resolvers_config=ResolversConfig(
                    secrets_resolver=secrets_resolver,
                    did_resolver=DIDResolverPeerDID()
                ),
                packed_msg= bob_packed_msg
            )
            print("Message ID:", msg_id)
            print(bob_msg.message.body["content"])


            alice_ack = Message(
                id = "unique-id-293e9a922efffxxxffsss",
                type = "https://didcomm.org/messagepickup/3.0/messages-received",
                body = {"message_id_list": [msg_id]}
            )

            alice_ack_packed_msg = await pack_encrypted(
                resolvers_config = ResolversConfig(
                    secrets_resolver = secrets_resolver,
                    did_resolver = DIDResolverPeerDID()
                ),
                message = alice_ack,
                to = mediator_did,
                frm = alice_did_for_mediator,
                sign_frm = None,
                pack_config = PackEncryptedConfig(protect_sender_id=False)
            )
            headers = {"Content-Type": "application/didcomm-encrypted+json"}
            resp5 = requests.post(mediator_endpoint, headers=headers, data = alice_ack_packed_msg.packed_msg)

            mediator_ack_status = await unpack(
                resolvers_config=ResolversConfig(
                    secrets_resolver=secrets_resolver,
                    did_resolver=DIDResolverPeerDID()
                ),
                packed_msg= resp5.json()
            )
        time.sleep(1)



asyncio.run(main())
