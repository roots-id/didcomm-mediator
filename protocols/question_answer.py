""" Basic Message Protocol 2.0 """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from importlib_metadata import metadata
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
import datetime


async def process_answer(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    print(unpack_msg.message.body)


async def submit_question(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    if unpack_msg.message.body["signature_required"]:
        response_signature = None 
    response_signature = None 
    response_message = Message(
        id=str(uuid.uuid4()),
        thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
        type="https://didcomm.org/questionanswer/2.0/question",
        custom_headers = [{
        "sent_time": int(datetime.datetime.now().timestamp())            
                    }],
        from_prior = from_prior,
        body={
            "response": "Are you in fron of the computer?",
            "response_signature": response_signature
        }
    )
    response_packed = await pack_encrypted(
        resolvers_config=ResolversConfig(
            secrets_resolver=get_secret_resolver(),
            did_resolver=DIDResolverPeerDID()
        ),
        message=response_message,
        frm=local_did,
        to=remote_did,
        sign_frm=None,
        pack_config=PackEncryptedConfig(protect_sender_id=False)
    )
    return response_packed.packed_msg
