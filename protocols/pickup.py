""" Pickup Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm.message import Attachment, AttachmentDataJson
from db_utils import get_message_status, get_messages, remove_messages


async def process_pickup_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    """ Process Pickup messages """
    if unpack_msg.message.type == "https://didcomm.org/messagepickup/3.0/status-request":
            return await process_status_request(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/messagepickup/3.0/delivery-request":
            return await process_delivery_request(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/messagepickup/3.0/messages-received":
            return await process_message_received(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/messagepickup/3.0/live-delivery-change":
            return await process_livedelivery_change(unpack_msg, remote_did, local_did, from_prior)


async def process_status_request(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    if  "recipient_key" in unpack_msg.message.body:
         recipient_key =  unpack_msg.message.body["recipient_key"]
    elif "recipient_did" in unpack_msg.message.body:
         recipient_key =  unpack_msg.message.body["recipient_did"]
    else:
        recipient_key = None
          
    count = get_message_status(remote_did, recipient_key)
    # TODO add optional info 
    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/messagepickup/3.0/status",
        body={
                "recipient_key": recipient_key,
                "message_count": count,
                # "longest_waited_seconds": 3600,
                # "newest_received_time": "2019-05-01 12:00:00Z",
                # "oldest_received_time": "2019-05-01 12:00:01Z",
                # "total_bytes": 8096,
                "live_delivery": False
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


async def process_delivery_request(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    recipient_key =  unpack_msg.message.body["recipient_did"] if "recipient_did" in unpack_msg.message.body else None
    limit = unpack_msg.message.body["limit"] 
    messages = get_messages(remote_did, recipient_key,int(limit))
    if len(list(messages)) == 0:
        response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/messagepickup/3.0/status",
        body={
                "recipient_key": recipient_key,
                "message_count": 0,
                "live_delivery": False
        },
        from_prior = from_prior
    )
    else:
        attachments = []
        for att in messages:
            attachments.append(Attachment(
                id=str(att["_id"]),
                data=AttachmentDataJson(json=att["attachment"]
                )
        ))
        # TODO add optional info 
        response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/messagepickup/3.0/delivery",
            body={
                    "recipient_key": recipient_key,
            },
            attachments = attachments,
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


async def process_message_received(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    message_id_list =  unpack_msg.message.body["message_id_list"]
    recipient_key =  unpack_msg.message.body["recipient_key"] if "recipient_key" in unpack_msg.message.body else None
    # remove messages info in DB
    remove_messages(remote_did, message_id_list)
    count = get_message_status(remote_did, recipient_key)

    response_message = Message(
    id=str(uuid.uuid4()),
    type="https://didcomm.org/messagepickup/3.0/status",
    body={
            "message_count": count,
            "live_delivery": False,
            # "longest_waited_seconds": 3600,
            # "newest_received_time": "2019-05-01 12:00:00Z",
            # "oldest_received_time": "2019-05-01 12:00:01Z",
            # "total_bytes": 8096,
            "live_delivery": False
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



async def process_livedelivery_change(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    if "live_delivery" in unpack_msg.message.body and unpack_msg.message.body["live_delivery"]:


        response_message = Message(
            id=str(uuid.uuid4()),
            pthid= unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/report-problem/2.0/problem-report",
            ack=unpack_msg.message.id,
            body={
                    "code": "e.m.live-delivery-not-supported",
                    "comment": "Connection does not support Live Delivery"
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