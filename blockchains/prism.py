from distutils.log import error
import sys
import os
import time
import jpype
import jpype.imports
from db_utils import get_prism_did, store_prism_did

try:
    sdk_gradle_home = os.environ["ATALA_PRISM_JARS"]
except KeyError:
    print("ERROR: `ATALA_PRISM_JARS` variable is not set.")
    print("Please, set it to the directory with Atala PRISM SDK dependencies JARs.")
    sys.exit(1)

try:
    jpype.imports.registerDomain('sdk', alias='io')
except ImportError as err:
    print(err.msg)
    sys.exit(1)
try:
    jpype.startJVM(
        classpath=[
            os.path.join(sdk_gradle_home, f) for f in os.listdir(sdk_gradle_home)
                if f.endswith('.jar')
        ]
    )

    from sdk.iohk.atala.prism.protos import *
    from sdk.iohk.atala.prism.api.node import *
    from sdk.iohk.atala.prism.api.models import *
    from sdk.iohk.atala.prism.api import *
    from sdk.iohk.atala.prism.crypto.derivation import *
    from sdk.iohk.atala.prism.crypto.keys import *
    from sdk.iohk.atala.prism.identity import *
    from kotlinx.serialization.json import *

    KeyGenerator = KeyGenerator.INSTANCE
    KeyDerivation = KeyDerivation.INSTANCE
    MasterKeyUsage = MasterKeyUsage.INSTANCE
    IssuingKeyUsage = IssuingKeyUsage.INSTANCE
    RevocationKeyUsage = RevocationKeyUsage.INSTANCE
    AuthenticationKeyUsage = AuthenticationKeyUsage.INSTANCE
    AtalaOperationStatus = AtalaOperationStatus.INSTANCE
except Exception as e:
    print("ERROR ",e)

def wait_until_confirmed(node_api: NodePublicApi, operation_id: AtalaOperationId):
    """Waits until operation is confirmed by Cardano network
    
    Confirmation doesn't necessarily mean that operation was applied.
    For example, it could be rejected because of an incorrect signature or other reasons.

    :param node_api: Atala PRISM Node API object
    :type node_api: NodePublicApi
    :param operation_id: Atala PRISM operation ID
    :type operation_id: AtalaOperationId
    """
    operation_status = int(node_api.getOperationInfo(operation_id).join().getStatus())
    while operation_status != AtalaOperationStatus.getCONFIRMED_AND_APPLIED() \
        and operation_status != AtalaOperationStatus.getCONFIRMED_AND_REJECTED():
        print(f"Current operation status: {AtalaOperationStatus.asString(operation_status)}")
        time.sleep(1)
        operation_status = int(node_api.getOperationInfo(operation_id).join().getStatus())

def prepare_keys_from_mnemonic(mnemonic: MnemonicCode, password: str):
    """Creates a map of potentially useful keys out of a mnemonic code

    :param mnemonic: Mnemonic to generate keys from
    :type mnemonic: MnemonicCode
    :param password: Password for seed generation
    :type password: str
    :return: Map of keys
    :rtype: dict<String, ECKeyPair>
    """
    did_key_map = {}
    seed = KeyDerivation.binarySeed(mnemonic, password)
    did_key_map[PrismDid.getDEFAULT_MASTER_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, MasterKeyUsage, 0)
    did_key_map[PrismDid.getDEFAULT_ISSUING_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, IssuingKeyUsage, 0)
    did_key_map[PrismDid.getDEFAULT_REVOCATION_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, RevocationKeyUsage, 0)
    return did_key_map

def prepare_keys_from_seed(seed: bytes):
    """Creates a map of potentially useful keys out of a mnemonic code

    :param seed: generated seed
    :type seed: bytes
    :return: Map of keys
    :rtype: dict<String, ECKeyPair>
    """
    did_key_map = {}
    did_key_map[PrismDid.getDEFAULT_MASTER_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, MasterKeyUsage, 0)
    did_key_map[PrismDid.getDEFAULT_ISSUING_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, IssuingKeyUsage, 0)
    did_key_map[PrismDid.getDEFAULT_REVOCATION_KEY_ID()] = KeyGenerator.deriveKeyFromFullPath(seed, 0, RevocationKeyUsage, 0)
    return did_key_map

def dictToJsonObjt(json: dict):
    resp = {}
    for key in json:
        if isinstance(json[key], str) or isinstance(json[key], int) or isinstance(json[key], float): 
            resp[key] = JsonLiteral(json[key], True)
        elif isinstance(json[key], dict): 
            resp[key] = dictToJsonObjt(json[key])
        elif isinstance(json[key], list): 
            resp[key] = listToJsonArray(json[key])
    return JsonObject(resp)

def listToJsonArray(array: list):
    resp = jpype.java.util.ArrayList()
    for el in array:
        if isinstance(el, str) or isinstance(el, int) or isinstance(el, float): resp.add(JsonLiteral(el, True))
        elif isinstance(el, dict): 
            resp.add(dictToJsonObjt(el))
        elif isinstance(el, dict): 
            resp.add(listToJsonArray(el))
    return JsonArray(resp)


environment = "ppp-node-test.atalaprism.io"
node_auth_api = NodeAuthApiAsyncImpl(GrpcOptions("http", environment, 50053))


async def create_prism_did():
    print("Issuer: Generates and registers a DID")
    seed = bytes(KeyDerivation.binarySeed(KeyDerivation.randomMnemonicCode(), "RootsId"))
    issuer_keys = prepare_keys_from_seed(seed)
    issuer_unpublished_did = PrismDid.buildLongFormFromMasterPublicKey(
        issuer_keys[PrismDid.getDEFAULT_MASTER_KEY_ID()].getPublicKey()
    )
    issuer_did = issuer_unpublished_did.asCanonical()
    store_prism_did(str(issuer_did), seed)


    node_payload_generator = NodePayloadGenerator(
        issuer_unpublished_did,
        {PrismDid.getDEFAULT_MASTER_KEY_ID(): issuer_keys[PrismDid.getDEFAULT_MASTER_KEY_ID()].getPrivateKey()}
    )
    issuer_create_did_info = node_payload_generator.createDid(PrismDid.getDEFAULT_MASTER_KEY_ID())
    issuer_create_did_operation_id = node_auth_api.createDid(
        issuer_create_did_info.getPayload(),
        issuer_unpublished_did,
        PrismDid.getDEFAULT_MASTER_KEY_ID()
    ).join()

    print(f"""
    - Issuer sent a request to create a new DID to PRISM Node.
    - The transaction can take up to 10 minutes to be confirmed by the Cardano network.
    - Operation identifier: {issuer_create_did_operation_id.hexValue()}
    """)
    create_did_operation_result = wait_until_confirmed(node_auth_api, issuer_create_did_operation_id)

    print(f"- DID with id {issuer_did} is created")
    return str(issuer_did)


async def issue_prism_credential(issuer_did, subject_did, json):
    claim = dictToJsonObjt(json)
    
    subject_prism_did = PrismDid.fromString(subject_did)
    issuer_seed = get_prism_did("did:prism:"+issuer_did.split(":")[2])["seed"]
    issuer_keys = prepare_keys_from_seed(issuer_seed)
    issuer_unpublished_did = PrismDid.buildLongFormFromMasterPublicKey(
        issuer_keys[PrismDid.getDEFAULT_MASTER_KEY_ID()].getPublicKey()
    )
    issuer_prism_did = issuer_unpublished_did.asCanonical()
    node_payload_generator = NodePayloadGenerator(
        issuer_unpublished_did,
        {
            PrismDid.getDEFAULT_MASTER_KEY_ID(): issuer_keys[PrismDid.getDEFAULT_MASTER_KEY_ID()].getPrivateKey(),
            PrismDid.getDEFAULT_ISSUING_KEY_ID(): issuer_keys[PrismDid.getDEFAULT_ISSUING_KEY_ID()].getPrivateKey()
        }
    )
    credential_claim = CredentialClaim(
        subject_prism_did,
        claim
    )
    issue_credential_info = node_payload_generator.issueCredentials(
        PrismDid.getDEFAULT_ISSUING_KEY_ID(),
        [credential_claim]
    )
    issue_credential_batch_operation_id = node_auth_api.issueCredentials(
        issue_credential_info.getPayload(),
        issuer_prism_did,
        PrismDid.getDEFAULT_ISSUING_KEY_ID(),
        issue_credential_info.getMerkleRoot()
        ).join()

    issue_credential_batch_operation_result = \
        wait_until_confirmed(node_auth_api, issue_credential_batch_operation_id)
    holder_signed_credential = issue_credential_info.getCredentialsAndProofs()[0].getSignedCredential()
    holder_credential_merkle_proof = issue_credential_info.getCredentialsAndProofs()[0].getInclusionProof()

    print(f"""
    - issueCredentialBatch operation identifier: {issue_credential_batch_operation_id.hexValue()}
    - Credential content: {holder_signed_credential.getContent()}
    - Signed credential: {holder_signed_credential.getCanonicalForm()}
    - Inclusion proof (encoded): {holder_credential_merkle_proof.encode()}
    - Batch id: {issue_credential_info.getBatchId()}"""
    )
    # TODO STORE CREDENTIAL
    return issue_credential_info



    
