""" Issue Credential 3.0 Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from issuer.credential_issuer import issue_credential

# TODO WE HAVE ONLY IMPLEMENTED  RREQUEST-CREDENTIAL AND ISSUE-CREDENTIAL
async def process_issue_credential_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Process Mediator Coordinator messages """
    if unpack_msg.message.type == "https://didcomm.org/issue-credential/3.0/request-credential":
            return await process_request_credential(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/issue-credential/3.0/ack":
            print("Verifiable Credential acknowledged")
            return
    elif unpack_msg.message.type == "https://didcomm.org/issue-credential/3.0/propose-credential":
            # TODO IMPLEMENT ERRORS
            return "ERROR"

async def process_request_credential(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):    
    response_message = await issue_credential(unpack_msg, remote_did, local_did, from_prior)
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

