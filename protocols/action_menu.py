""" Action Menu 2.0 Protocol """
from didcomm.message import Message, FromPrior
import uuid
from didcomm.pack_encrypted import pack_encrypted, PackEncryptedConfig, PackEncryptedResult
from didcomm.common.resolvers import ResolversConfig
from didcomm.unpack import UnpackResult
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from protocols.question_answer import submit_question
import datetime
import os
import urllib.parse
import requests

async def process_action_menu_message(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    if unpack_msg.message.type == "https://didcomm.org/action-menu/2.0/menu-request":
            return await process_menu_request(unpack_msg, remote_did, local_did, from_prior)
    elif unpack_msg.message.type == "https://didcomm.org/action-menu/2.0/perform":
            return await process_perform(unpack_msg, remote_did, local_did, from_prior)

async def process_menu_request(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):

    # TODO GET MENU FROM DB
    menu = {
        "title": "RootsID Issuer",
        "description": "RootsID demo issuer",
        "errormsg": None,
        "options": [
            {
                "name": "form-example",
                "title": "Form Example",
                "description": "Form to be filled in and submitted",
                "form": {
                    "description": "Please provide the following information",
                    "params": [
                        {
                            "name": "name",
                            "title": "Name",
                            "default": "",
                            "description": "",
                            "required": True,
                            "type": "text"
                        },
                                            {
                            "name": "lastname",
                            "title": "Last name",
                            "default": "",
                            "description": "",
                            "required": True,
                            "type": "text"
                        }
                    ],
                    "submit-label": "Submit form"
                }
            },
            {
                "name": "ask-me-example",
                "title": "Askme anything",
                "description": "Wolfram alpha will respond",
                "form": {
                    "description": "Ask me a question",
                    "params": [
                        {
                            "name": "question",
                            "title": "Question",
                            "type": "text"
                        }
                    ],
                    "submit-label": "Ask"
                }
            },
            {
                "name": "trigger-questionanswer",
                "title": "Trigger a question ",
                "description": "Trigger a question message using questionanswer protocol"
            },
        ]
    } 

    response_message = Message(
        id=str(uuid.uuid4()),
        type="https://didcomm.org/action-menu/2.0/menu",
        body=menu,
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

async def process_perform(unpack_msg: UnpackResult, remote_did, local_did, from_prior: FromPrior):
    # TODO PERFROM ACTION FROM DB OR EXTERNAL
    perform_action = unpack_msg.message.body["name"]
    if perform_action == "form-example":
        response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/basicmessage/2.0/message",
            body={"content": "Hello " + unpack_msg.message.body["params"]["name"] + " " + unpack_msg.message.body["params"]["lastname"]},
            custom_headers = [{
            "sent_time": int(datetime.datetime.now().timestamp())            
                        }],
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
    elif perform_action == "ask-me-example":
        question = urllib.parse.quote(unpack_msg.message.body["params"]["question"])
        if "WOLFRAM_ALPHA_API_ID" in os.environ:
            answer = requests.get("http://api.wolframalpha.com/v1/result?i="+question+"&appid="+os.environ["WOLFRAM_ALPHA_API_ID"]).text
        else: 
            answer = "No Wolfram Apha API ID in server"
        response_message = Message(
            id=str(uuid.uuid4()),
            thid=unpack_msg.message.id if not unpack_msg.message.thid else unpack_msg.message.thid,
            type="https://didcomm.org/basicmessage/2.0/message",
            body={"content": answer},            custom_headers = [{
            "sent_time": int(datetime.datetime.now().timestamp())            
                        }],
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
    elif perform_action == "trigger-questionanswer":
        await submit_question()
    else: 
        return await process_menu_request(unpack_msg,remote_did, local_did, from_prior)

