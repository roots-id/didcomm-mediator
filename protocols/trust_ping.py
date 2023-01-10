""" Trust Ping Protocol 2.0 """
import uuid
from didcomm.message import Message
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig
from didcomm.unpack import UnpackResult
from didcomm.common.resolvers import ResolversConfig
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm_v2.send_http_message import send_http_msg



async def process_trust_ping(unpack_msg:UnpackResult):
    """ Response to Trust Ping message """
    if unpack_msg.message.body["response_requested"]:
        response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id,
            type="https://didcomm.org/trust-ping/2.0/ping-response",
            body={}
        )
        response_packed = await pack_encrypted(
            resolvers_config=ResolversConfig(
                secrets_resolver=get_secret_resolver(),
                did_resolver=DIDResolverPeerDID()
            ),
            message=response_message,
            frm=unpack_msg.metadata.encrypted_to[0].split("#")[0],
            to=unpack_msg.metadata.encrypted_from.split("#")[0],
            sign_frm=None,
            pack_config=PackEncryptedConfig(protect_sender_id=False)
        )
        # await send_http_msg(response_packed, unpack_msg.metadata.encrypted_from.split("#")[0], unpack_msg.metadata.encrypted_to[0].split("#")[0])
        return response_packed.packed_msg