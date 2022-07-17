""" Mediator Coordination Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from importlib_metadata import metadata
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm_v2.peer_did import create_peer_did
from db_utils import get_connection, add_mediation, update_keys


async def process_mediator_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Process Mediator Coordinator messages """
    if unpack_msg.message.type == "https://didcomm.org/coordinate-mediation/2.0/mediate-request":
            return await process_mediate_request(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/coordinate-mediation/2.0/keylist-update":
            return await process_keylist_update(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/coordinate-mediation/2.0/keylist-query":
            return await process_keylist_query(unpack_msg, remote_did, local_did, from_prior)

async def process_mediate_request(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # check if already a connection and deny
    if "isMediation" in get_connection(remote_did) and get_connection(remote_did)["isMediation"]:
        response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/coordinate-mediation/2.0/mediate-deny",
        body={},
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

    routing_key = await create_peer_did(1, 1, service_endpoint="http://127.0.0.1:8000")
    endpoint = "http://127.0.0.1:8000"
    add_mediation(remote_did, routing_key, endpoint)
    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/coordinate-mediation/2.0/mediate-grant",
        body={
            "endpoint": endpoint,
            "routing_keys": [routing_key]
        },
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

async def process_keylist_update(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    updated = update_keys(remote_did, unpack_msg.message.body["updates"])

    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/coordinate-mediation/2.0/keylist-update-response",
        body={
            "updated": updated,
        },
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

async def process_keylist_query(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # TODO ADD PAGINATION
    connection = get_connection(remote_did)
    keylist = connection["keylist"] if "keylist" in connection else []
    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/coordinate-mediation/2.0/keylist",
        body={
            "keys": [{"recipient_key": k} for k in keylist]
        },
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