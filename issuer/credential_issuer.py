""" Credential Issuer """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.unpack import UnpackResult
from db_utils import get_issuer_did, store_vc , get_vc
import datetime
from didcomm.message import Attachment, AttachmentDataJson
from blockchains.prism import issue_prism_credential
import json

async def issue_credential(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # 1-Validate credential request
    # TODO validate if attachements and add multiple attachments
    attachment = unpack_msg.message.attachments[0]
    # TODO throw error if format is not supported
    # TODO validate options
    #if attachment.format == "aries/ld-proof-vc-detail@v1.0":
    id_to_search = attachment.data.json['credential']['id']
    credential = get_vc(id_to_search)
    print('local credential retrieved')
    print(credential)
    if credential:
        credential.pop('_id')
    if credential == None:
        vc_detail = attachment.data.json
        credential = vc_detail["credential"]
        holder_did = credential["credentialSubject"]["id"]
        # TODO validate if did:prism
        issuer_did = get_issuer_did()['did']
        #MUST BE PRISM
        credential["issuer"] = issuer_did
        credential["issuanceDate"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        print('credential to issue')
        print(credential)
        # 2- Call dataseers (TODO)
        # 3 - Call Prism
        prism_credential_info = await issue_prism_credential(issuer_did, holder_did,credential)
        holder_signed_credential = prism_credential_info.getCredentialsAndProofs()[0].getSignedCredential()
        holder_credential_merkle_proof = prism_credential_info.getCredentialsAndProofs()[0].getInclusionProof()
        credential["proof"] = {
            "type": "EcdsaSecp256k1Signature2019",
            "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "verificationMethod": issuer_did,
            "proofPurpose": "assertionMethod",
            "proofValue": str(holder_signed_credential.getCanonicalForm()),
            "proofHash": json.loads(str(holder_credential_merkle_proof.encode()))["hash"],
            "proofBatchId": str(prism_credential_info.getBatchId().getId())
        }        

         # 4- Respond with issue-credential
        print('credential issued and stored locally')
        print(credential)
        store_vc(credential)
        
    else:
        pass
    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/issue-credential/3.0/issue-credential",
        body=unpack_msg.message.body,
        from_prior = from_prior,
        attachments = [
        Attachment(
                id=str(uuid.uuid4()),
                media_type= "application/json",
                format= "aries/ld-proof-vc-detail@v1.0",
                data=AttachmentDataJson(json=credential)
                )
            ]
        )
    return response_message