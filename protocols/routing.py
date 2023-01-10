""" Routing Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from importlib_metadata import metadata
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from db_utils import add_message


async def process_forward_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # TODO REMOVE COMMENT AND FIX IF SENTENCE
    # check if comply with headers
    # if unpack_msg.message.expires_time or "delay_milli" in unpack_msg.message.custom_headers:
    #     #report problem
    #     response_message = Message(
    #             id=str(uuid.uuid4()),
    #             pthid= unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
    #             type="https://didcomm.org/report-problem/2.0/problem-report",
    #             ack=unpack_msg.message.id,
    #             body={
    #                     "code": "e.m.header-not-supported",
    #                     "comment": "expiry time or delay not supported"
    #             },
    #             from_prior = from_prior
    #         )
    
    #     response_packed = await pack_encrypted(
    #         resolvers_config=ResolversConfig(
    #             secrets_resolver=get_secret_resolver(),
    #             did_resolver=DIDResolverPeerDID()
    #         ),
    #         message=response_message,
    #         frm=local_did,
    #         to=remote_did,
    #         sign_frm=None,
    #         pack_config=PackEncryptedConfig(protect_sender_id=False)
    #     )
    #     return response_packed.packed_msg
    
    # STORE MESSAGES
    for attachment in unpack_msg.message.attachments:
        recipient_key = unpack_msg.message.body["next"]
        add_message(recipient_key, attachment.data.json)
