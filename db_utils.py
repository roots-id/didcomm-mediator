''' DB Utilities '''
from pymongo import MongoClient
import datetime

mongo = MongoClient()
db = mongo.mediator

def get_connection(remote_did):
    ''' Get existing connection '''
    return db.connections.find_one({"remote_did": remote_did})

def create_connection(remote_did, local_did):
    ''' Create connection'''
    db.connections.insert_one({
        "remote_did": remote_did,
        "local_did": local_did,
        "creation_time": int(datetime.datetime.now().timestamp())
    })

def update_connection(remote_old_did, remote_new_did):
    ''' Update connection '''
    #TODO history of rotations
    db.connections.update_one(
        {"remote_did": remote_old_did}, {
            "$set": {"remote_did": remote_new_did, "update_time": int(datetime.datetime.now().timestamp())}
        }
    )

def get_oob_did():
    return db.oobs.find_one()

def store_oob_did(did):
    db.oobs.insert_one(did)

def add_mediation(remote_did, routing_key, endpoint):
    ''' Add mediation info to connection '''
    db.connections.update_one(
        {"remote_did": remote_did}, {
            "$set": {
                        "isMediation": True, 
                        "routing_key": routing_key,
                        "endpoint": endpoint
                    }
        }
    )

def update_keys(remote_did, updates):
    ''' Add mediation keys '''
    connection = get_connection(remote_did)
    current_keys = connection["keylist"] if "keylist" in connection else []
    updated = []
    for update in updates:
        if update["action"] == "add":
            if update["recipient_key"] in current_keys:
                updated.append(
                    {
                        "recipient_key": update["recipient_key"],
                        "action": "add",
                        "result": "no_change"
                    })
            else:
                current_keys.append(update["recipient_key"])
                updated.append(
                    {
                        "recipient_key": update["recipient_key"],
                        "action": "add",
                        "result": "success"
                    })
        elif update["action"] == "remove":
            if update["recipient_key"] in current_keys:
                current_keys.remove(update["recipient_key"])
                updated.append(
                    {
                        "recipient_key": update["recipient_key"],
                        "action": "remove",
                        "result": "success"
                    })
            else:
                updated.append(
                    {
                        "recipient_key": update["recipient_key"],
                        "action": "remove",
                        "result": "no_change"
                    })
        else:
            updated.append(
                    {
                        "recipient_key": update["recipient_key"],
                        "action": update["action"],
                        "result": "client_error"
                    })
        db.connections.update_one(
        {"remote_did": remote_did}, {
            "$set": {
                        "keylist": current_keys, 
                    }
        }
    )
    return updated

def get_message_status(remote_did, recipient_key):
    if recipient_key:
        count = db.messages.find({"recipient_key": recipient_key},{"attachment":1}).count()
    else:
        recipient_keys = db.conections.find_one({"remote_did":remote_did},{"keylist":1})
        count = db.messages.find({"recipient_key": {"$in":recipient_keys}},{"attachment":1}).count()
    return count

def get_messages(remote_did, recipient_key,limit):
    if recipient_key:
        return db.messages.find({"recipient_key": recipient_key},{"attachment":1}).limit(limit)
    else:
        recipient_keys = db.conections.find_one({"remote_did":remote_did},{"keylist":1})
        return db.messages.find({"recipient_key": {"$in":recipient_keys}},{"attachment":1}).limit(limit)

def add_message(recipient_key, attachment):
    # TODO verify that recipient_key belong to a registered peer
    db.messages.insert_one(
            {
                "recipient_key": recipient_key,
                "attachment": attachment,
                "datetime": int(datetime.datetime.now().timestamp())
            }
        )

def remove_messages(remote_did, message_id_list):
    #TODO verify that recipient_key belongs to remote_did
    for id in message_id_list:
        db.messages.find_one({"_id": id, "recipient_key": recipient_key})
    return get_message_status(remote_did, None)
