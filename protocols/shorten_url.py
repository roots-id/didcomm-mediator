""" Shorten URL 1.0 Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from importlib_metadata import metadata
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from db_utils import store_short_url, expire_short_url
import datetime
import os

async def process_shorten_url_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    if unpack_msg.message.type == "https://didcomm.org/shorten-url/1.0/request-shortened-url":
        return await process_shortened_url_request(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/shorten-url/1.0/invalidate-shortened-url":
        return await process_invalidate(unpack_msg, remote_did, local_did, from_prior)

async def process_shortened_url_request(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    long_url = unpack_msg.message.body["url"]
    requested_validity_seconds = unpack_msg.message.body["requested_validity_seconds"]
    short_url_slug = "/"+unpack_msg.message.body["short_url_slug"] if "short_url_slug" in unpack_msg.message.body else ""
    goal_code = unpack_msg.message.body["goal_code"]
    if goal_code == "shorten.oobv2":
        oobid = str(uuid.uuid4()).replace("-","")
        date = int(datetime.datetime.now().timestamp())*1000
        expires_time = int(date + requested_validity_seconds * 1000)
        server_url = os.environ["PUBLIC_URL"] if "PUBLIC_URL" in os.environ  else "http://127.0.0.1:8000"
        short_url = server_url + "/qr" + short_url_slug + "?_oobid=" + oobid
        store_short_url(
            {
                "date": date,
                "expires_time": expires_time,
                "requested_validity_seconds": requested_validity_seconds,
                "long_url": long_url,
                "oobid": oobid,
                "short_url_slug": short_url_slug,
                "goal_code": goal_code
            }
        )
        response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/shorten-url/1.0/shortened-url",
            body={
                "shortened_url": short_url,
                "expires_time": int(expires_time/1000)
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
    else:
        # TODO Report Problem
        return

async def process_invalidate(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    shortened_url = unpack_msg.message.body["shortened_url"]
    oobid = shortened_url.split("=")[1]
    print("obid",oobid)
    expire_short_url(oobid)
    response_message = Message(
        id=str(uuid.uuid4()),
        ack=unpack_msg.message.id,
        type="https://didcomm.org/empty/1.0/empty",
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
