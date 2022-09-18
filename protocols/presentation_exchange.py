""" Presentation Exchange 3.0 Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from issuer.credential_issuer import issue_credential
from didcomm.message import Attachment, AttachmentDataJson
from blockchains.prism import verify_proofhash, verify_prism_credential
#currently implemented as a simple pass-through, data still not validated and no credentials work yet since signatures are not aligned
async def process_presentation_exchange_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Process Mediator Coordinator messages """
    if unpack_msg.message.type == "https://didcomm.org/out-of-band/2.0/invitation" and \
        unpack_msg.message.body["goal_code"] == "streamlined-vp":
        return await process_oob_vp_invitation(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/present-proof/3.0/propose-presentation":
            return await process_propose_presentations(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/present-proof/3.0/presentation":
            return await process_request_presentations(unpack_msg, remote_did, local_did, from_prior)

#https://identity.foundation/waci-didcomm/#step-2-send-message-proposing-presentation
async def process_oob_vp_invitation(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    response_packed = await pack_encrypted(
        resolvers_config=ResolversConfig(
            secrets_resolver=get_secret_resolver(),
            did_resolver=DIDResolverPeerDID()
        ),
        message={},
        type="https://didcomm.org/present-proof/3.0/propose-presentation",
        id=str(uuid.uuid4()),
        thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
        pthid=unpack_msg.message.id,
        frm=local_did,
        to=remote_did,
        sign_frm=None,
        pack_config=PackEncryptedConfig(protect_sender_id=False)
    )
    return response_packed.packed_msg
#https://identity.foundation/waci-didcomm/#step-3-send-message-requesting-presentation
async def process_propose_presentations(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """
    Propose presentation protocol should generate a presentation request and send it to the holder
    """

    options = {
            "challenge": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
            "domain": "4jt78h47fh47"
          }
    presentation_definition = {"presentation_definition": {
            "id": "32f54163-7166-48f1-93d8-ff217bdb0654",
            "input_descriptors": [{
                "id": "66685f64-7166-5717-b3fc-ff217bdb9999",
                "constraints": {
                "fields": [
                    {
                    "path": [
                        "$.type"
                    ],
                    "filter": {
                        "type": "string",
                        "pattern": "UniversityDegreeCredential"
                    }
                    }
                ]
                }
            }
    ]
          }
    }

    response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/present-proof/3.0/request-presentation",
            body={},
            attachments=[Attachment(
                id=str(uuid.uuid4()),
                format="dif/presentation-exchange/definitions@v1.0",
                media_type="application/json",
                data=AttachmentDataJson(json=({"presentation_definition": presentation_definition, "options": options}))
                )],
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


#https://identity.foundation/waci-didcomm/#step-4-present-proof
async def process_request_presentations(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """
    Request presentation protocol should generate a presentation and send it to the verifier
    """

    attachment = unpack_msg.message.attachments[0]
    submission = attachment.data.json 
    errors = verify_prism_credential(submission["verifiableCredential"][0])
    if len(errors) > 0:
        prism_credential_status = False
    else:
        prism_credential_status = True

    status = verify_proofhash(submission['verifiableCredential'][0], submission['proof']['challenge'], submission['proof']['proofValue'], submission['proof']['verificationMethod'])
    print("*** Proof Status: ", status)
    

    response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/present-proof/3.0/ack",
            body={'status': 'OK',
                'proof-status': status,
                'prism_credential_status': prism_credential_status}
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