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

#currently implemented as a simple pass-through, data still not validated and no credentials work yet since signatures are not aligned
async def process_presentation_exchange_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Process Mediator Coordinator messages """
    if unpack_msg.message.type == "https://didcomm.org/out-of-band/2.0/invitation" and \
        unpack_msg.message.body["goal_code"] == "streamlined-vp":
        return await process_oob_vp_invitation(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/present-proof/3.0/propose-presentation":
            return await process_propose_presentations(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/present-proof/3.0/ack":
            print("Verifiable Credential acknowledged")
            return

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
            "frame": {
              "@context": [
                "https://www.w3.org/2018/credentials/v1",
                "https://w3id.org/vaccination/v1"
              ],
              "type": [
                "VerifiableCredential",
                "VaccinationCertificate"
              ],
              "credentialSubject": {
                "@explicit": True,
                "type": [
                  "VaccinationEvent"
                ],
                "batchNumber": {},
                "countryOfVaccination": {}
              }
            },
            "input_descriptors": [
              {
                "id": "vaccination_input",
                "name": "Vaccination Certificate",
                "constraints": {
                  "fields": [
                    {
                      "path": [
                        "$.credentialSchema.id", "$.vc.credentialSchema.id"
                      ],
                      "filter": {
                        "type": "string",
                        "const": "https://w3id.org/vaccination/#VaccinationCertificate"
                      }
                    },
                    {
                      "path": [
                        "$.credentialSubject.batchNumber"
                      ],
                      "filter": {
                        "type": "string"
                      }
                    },
                    {
                      "path": [
                        "$.credentialSubject.countryOfVaccination"
                      ],
                      "filter": {
                        "type": "string"
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
                data={"presentation_definition": presentation_definition, "options": options}
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
    attachment['presentation_definition']['id']
    attachment['presentation_definition']['input_descriptors'][0]['id']
    proof = {
         "@context":[
            "https://www.w3.org/2018/credentials/v1",
            "https://identity.foundation/presentation-exchange/submission/v1"
         ],
         "type":[
            "VerifiablePresentation",
            "PresentationSubmission"
         ],
         "holder":"did:example:123",
         "verifiableCredential":[
            {
               "@context":[
                  "https://www.w3.org/2018/credentials/v1",
                  "https://w3id.org/vaccination/v1"
               ],
               "id":"urn:uvci:af5vshde843jf831j128fj",
               "type":[
                  "VerifiableCredential",
                  "VaccinationCertificate"
               ],
               "description":"COVID-19 Vaccination Certificate",
               "name":"COVID-19 Vaccination Certificate",
               "expirationDate":"2029-12-03T12:19:52Z",
               "issuanceDate":"2019-12-03T12:19:52Z",
               "issuer":"did:example:456",
               "credentialSubject":{
                  "id":"urn:bnid:_:c14n2",
                  "type":"VaccinationEvent",
                  "batchNumber":"1183738569",
                  "countryOfVaccination":"NZ"
               },
               "proof":{
                  "get":"stored proof in mongo?"
               }
            }
         ],
         "presentation_submission":{
            "id":"1d257c50-454f-4c96-a273-c5368e01fe63",
            "definition_id":attachment['presentation_definition']['id'], #fetch from previous request
            "descriptor_map":[
               {
                  "id":attachment['presentation_definition']['input_descriptors'][0]['id'],
                  "format":"ldp_vp",
                  "path":"$.verifiableCredential[0]"
               }
            ]
         },
         "proof":{
            "type":"Ed25519Signature2018",
            "verificationMethod":"did:example:123#key-0",
            "created":"2021-05-14T20:16:29.565377",
            "proofPurpose":"authentication",
            "challenge":attachment['options']['challenge'],
            "jws":"eyJhbGciOiAiRWREU0EiLCAiYjY0IjogZmFsc2UsICJjcml0IjogWyJiNjQiXX0..7M9LwdJR1_SQayHIWVHF5eSSRhbVsrjQHKUrfRhRRrlbuKlggm8mm_4EI_kTPeBpalQWiGiyCb_0OWFPtn2wAQ"
         }
      }
