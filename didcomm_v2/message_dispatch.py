""" Protocol Routing """
from didcomm.unpack import UnpackResult
from didcomm.message import FromPrior
from didcomm_v2.peer_did import create_peer_did
from protocols.trust_ping import process_trust_ping
from protocols.basic_message import process_basic_message
from protocols.question_answer import process_answer
from protocols.mediator_coordination import process_mediator_message
from protocols.routing import process_forward_message
from protocols.pickup import process_pickup_message
from protocols.discover_features import process_discover_queries
from protocols.action_menu import process_action_menu_message
from protocols.shorten_url import process_shorten_url_message
from db_utils import create_connection, get_connection, update_connection
import os
if "PRISM_ISSUER" in os.environ and os.environ["PRISM_ISSUER"]==1:
    from protocols.issue_credential import process_issue_credential_message


async def message_dispatch(unpack_msg:UnpackResult):
    """ Selecting the correct protocol base on message type """
    if unpack_msg.message.type == "https://didcomm.org/trust-ping/2.0/ping":
        return await process_trust_ping(unpack_msg)
    else:
        # For all protocols except ping, store connection and rotate did if needed
        
        # check sender did rotation
        if unpack_msg.message.from_prior:
            sender_old_did = unpack_msg.message.from_prior.iss 
            sender_did = unpack_msg.message.from_prior.sub
        else:
            sender_did = unpack_msg.metadata.encrypted_from.split("#")[0]
            sender_old_did = sender_did
        
        # Check if connection exist
        connection = get_connection(sender_old_did)
        if not connection:
            #allways rotate DID if unknown connection
            connection_did = await create_peer_did(1, 1, service_endpoint=os.environ["PUBLIC_URL"])
            from_prior = FromPrior(iss=unpack_msg.metadata.encrypted_to[0].split("#")[0], sub=connection_did)
            create_connection(sender_did, connection_did)
        else:
            connection_did = connection["local_did"]
            from_prior = None
            if unpack_msg.message.from_prior:
                update_connection(sender_old_did, sender_did)

        # Routing base on message type
        if unpack_msg.message.type == "https://didcomm.org/questionanswer/2.0/answer":
            return process_answer(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type == "https://didcomm.org/basicmessage/2.0/message":
            return await process_basic_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type.startswith("https://didcomm.org/coordinate-mediation/2.0/"):
            return await process_mediator_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type.startswith("https://didcomm.org/messagepickup/3.0/"):
            return await process_pickup_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type == "https://didcomm.org/routing/2.0/forward":
            return await process_forward_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type == "https://didcomm.org/discover-features/2.0/queries":
            return await process_discover_queries(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type.startswith("https://didcomm.org/issue-credential/3.0/"):
            return await process_issue_credential_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type.startswith("https://didcomm.org/action-menu/2.0/"):
            return await process_action_menu_message(unpack_msg, sender_did, connection_did, from_prior)
        elif unpack_msg.message.type.startswith("https://didcomm.org/shorten-url/1.0/"):
            return await process_shorten_url_message(unpack_msg, sender_did, connection_did, from_prior)

