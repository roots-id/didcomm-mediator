""" Discover Features 2.0 protocol"""
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
import re
supported_protocols = [
    "https://didcomm.org/basicmessage/2.0",
    "https://didcomm.org/coordinate-mediation/2.0",
    "https://didcomm.org/messagepickup/3.0",
    "https://didcomm.org/out-of-band/2.0",
    "https://didcomm.org/trust-ping/2.0",
    "https://didcomm.org/discover-features/2.0"
]

async def process_discover_queries(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Response to Queries message. Only protocols queries are supported. No roles are not reported """
    queries = unpack_msg.message.body["queries"]
    disclosures = []
    for query in queries:
        if query["feature-type"] == "protocol":
            for supported_protocol in supported_protocols:
                if re.match(".*" if query["match"]=="*" else query["match"], supported_protocol): 
                    disclosures.append({
                        "feature-type": "protocol",
                        "id": supported_protocol
                    })

    response_message = Message(
        id=str(uuid.uuid4()),
        thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
        type="https://didcomm.org/discover-features/2.0/disclose",
        body={"disclosures": disclosures},
        from_prior = from_prior
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
