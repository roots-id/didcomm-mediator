""" Credential Issuer """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.unpack import UnpackResult
from db_utils import get_issuer_did
import datetime
from didcomm.message import Attachment, AttachmentDataJson
from blockchains.prism import issue_prism_credential
import json
from jose import jws



async def issue_credential(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # 1-Validate credential request
    # TODO validate if attachements and add multiple attachments
    attachment = unpack_msg.message.attachments[0]
    # TODO throw error if format is not supported
    # TODO validate options
    #if attachment.format == "aries/ld-proof-vc-detail@v1.0":
    if True:
        vc_detail = attachment.data.json
        credential = vc_detail["credential"]
        holder_did = credential["credentialSubject"]["id"]
        # THIS IS FOR DEMO PURPOSES
        # Select type of issuanse based on holder DID
        if holder_did.startswith("did:prism"):
            issuer_did = get_issuer_did()
            credential["issuer"] = issuer_did
            credential["issuanceDate"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

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
        else:
            # USE DID:PEER
            issuer_did = local_did
            credential["issuer"] = {
                "type": "Profile",
                "id": issuer_did,
                "name": "IIW 2022",
                "url": "https://www.jff.org/",
                "image": "https://kayaelle.github.io/vc-ed/plugfest-1-2022/images/JFF_LogoLockup.png"
            }
            
            credential["issuanceDate"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

            print(credential)
            ## TODO This is FAKE, siging with fake secret no related to DID
            signed = jws.sign(credential, 'secret', algorithm='HS256')
            
            credential["proof"] =  {
                "type": "Ed25519Signature2018",
                "created": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "verificationMethod": issuer_did,
                "proofPurpose": "assertionMethod",
                "jws": signed
            }
               

         # 4- Respond with issue-credential
    
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
    else:
        # TODO RETURN ERROR
        return "ERROR"