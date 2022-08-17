""" Credential Issuer """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID


async def issue_credential(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # 1-Validate credential request
    # TODO validate if attachements and add multiple attachments
    attachment = unpack_msg.message.attachments[0]
    # TODO throw error if format is not supported
    if attachment.format == "dif/credential-manifest@v1.0":
        credential_manifest = attachment.data.json        
        issuer_requested = credential_manifest["issuer"]
        credential_requested = credential_manifest["credential"]
        evidence = ""
        subject = "" # validate if prism

        # 2- Issue credential
        # TODO ISSUE PRISM CREDENTIAL
        prism_credetial = ""


    # 3- Respond with issue-credential
    
        response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/issue-credential/3.0/issue-credential",
        body={},
        from_prior = from_prior
        )

        return response_message
    else:
        # TODO RETURN ERROR
        return "ERROR"