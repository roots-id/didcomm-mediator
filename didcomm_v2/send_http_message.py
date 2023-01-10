from didcomm_v2.peer_did import resolve_peer_did, create_peer_did
from didcomm.message import Message
from didcomm.message import Attachment, AttachmentDataJson
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig
from didcomm.common.resolvers import ResolversConfig
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm_v2.peer_did import get_secret_resolver
from peerdid import peer_did
import requests
import json
import os
import uuid




async def send_http_msg(packed_msg, to_did: str, from_did: str):
    """ Send a DIDComm message over HTTP """
    to_did_doc = json.loads(peer_did.resolve_peer_did(to_did))
    service_endpoint = to_did_doc["service"][0]["serviceEndpoint"]

    if type(service_endpoint) ==  str and service_endpoint.startswith("http"):
        await send_direct_message(packed_msg, service_endpoint)
    elif type(service_endpoint) ==  str and service_endpoint.startswith("did:peer"):
        await send_forward_message(packed_msg, to_did, service_endpoint)
    elif  type(service_endpoint) == list and len(service_endpoint)>0:
        s = service_endpoint[0]
        if "uri" in s and s["uri"].startswith("http"):
            await send_direct_message(packed_msg, s["uri"])
        elif "uri" in s and s["uri"].startswith("did:peer"):
            await send_forward_message(packed_msg, to_did, s["uri"])
    else:
        print("ERROR: No service endpoint found")
        
    
async def send_direct_message(packed_msg, url: str):
    print("Sending HTTP message")
    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    resp = requests.post(url, headers=headers, json = json.loads(packed_msg.packed_msg))
    print(resp.status_code)
    # TODO handle errors

async def send_forward_message(packed_msg, to_did: str, forward_did: str):
    # get mediator endpoint
    forward_did_doc = json.loads(peer_did.resolve_peer_did(forward_did))
    forward_endpoint = forward_did_doc["service"][0]["serviceEndpoint"]
    public_url = os.environ["PUBLIC_URL"] if "PUBLIC_URL" in os.environ  else "http://127.0.0.1:8000"
    ephemeral_did = await create_peer_did(1, 1, service_endpoint=public_url)
    forward_message = Message(
    id = str(uuid.uuid4()),
        type="https://didcomm.org/routing/2.0/forward",
        body={"next": to_did},
        to=[forward_did],
        attachments=[Attachment(
                data=AttachmentDataJson(json=json.loads(packed_msg.packed_msg))
            )]
    )
    forward_message_packed = await pack_encrypted(
        resolvers_config = ResolversConfig(
            secrets_resolver = get_secret_resolver(),
            did_resolver = DIDResolverPeerDID()
        ),
        message = forward_message,
        frm = ephemeral_did,
        to = forward_did,
        sign_frm = None,
        pack_config = PackEncryptedConfig(protect_sender_id=False)
    )
        
    print("Sending HTTP forward message")
    headers = {"Content-Type": "application/didcomm-encrypted+json"}
    resp = requests.post(forward_endpoint, headers=headers, json = json.loads(forward_message_packed.packed_msg))
    print(resp.status_code)
    # TODO handle errors
    



