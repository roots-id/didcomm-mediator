''' DB Utilities '''
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import os
import urllib.parse


mongo = MongoClient(
    os.environ["DB_URL"],
    username=urllib.parse.quote_plus(os.environ["MONGODB_USER"]) if "MONGODB_USER" in os.environ else None,
    password=urllib.parse.quote_plus(os.environ["MONGODB_PASSWORD"]) if "MONGODB_PASSWORD" in os.environ else None,
    authSource="admin"
)


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
    return db.oobs.find_one(sort=[('date', -1)])

def store_oob_did(did):
    db.oobs.insert_one(did)

def del_issuers():
    db.messaissuersges.delete_many({})
    
def get_demo_issuer_did():
    #get the issuer whose did fields starts with "did:peer"
    
    issuer_did= db.issuers.find_one({"did": {"$regex": "^did:key"}},sort=[('date', -1)])
    # issuer_did = db.issuers.find_one(sort=[('date', -1)])
    return issuer_did


def add_mediation(remote_did, routing_did, endpoint):
    ''' Add mediation info to connection '''
    db.connections.update_one(
        {"remote_did": remote_did}, {
            "$set": {
                        "isMediation": True, 
                        "routing_did": routing_did,
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
            if update["recipient_did"] in current_keys:
                updated.append(
                    {
                        "recipient_did": update["recipient_did"],
                        "action": "add",
                        "result": "no_change"
                    })
            else:
                current_keys.append(update["recipient_did"])
                updated.append(
                    {
                        "recipient_did": update["recipient_did"],
                        "action": "add",
                        "result": "success"
                    })
        elif update["action"] == "remove":
            if update["recipient_did"] in current_keys:
                current_keys.remove(update["recipient_did"])
                updated.append(
                    {
                        "recipient_did": update["recipient_did"],
                        "action": "remove",
                        "result": "success"
                    })
            else:
                updated.append(
                    {
                        "recipient_did": update["recipient_did"],
                        "action": "remove",
                        "result": "no_change"
                    })
        else:
            updated.append(
                    {
                        "recipient_did": update["recipient_did"],
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
        count = db.messages.count_documents({"recipient_key": recipient_key},{"attachment":1})
    else:
        resp = db.connections.find_one({"remote_did":remote_did})
        if "keylist" in resp : 
            recipient_keys = resp["keylist"]
            count = db.messages.count_documents({"recipient_key": {"$in":recipient_keys}})
        else:
            count = 0
    return count

def get_messages(remote_did, recipient_key,limit):
    if recipient_key:
        return db.messages.find({"recipient_key": recipient_key},{"attachment":1}).limit(limit)
    else:
        recipient_keys = db.connections.find_one({"remote_did":remote_did})["keylist"]
        return list(db.messages.find({"recipient_key": {"$in":recipient_keys}}).limit(limit))

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
        db.messages.delete_one({"_id": ObjectId(id)})
    return get_message_status(remote_did, None)

def get_short_url(oobid):
    short_url = db.shortUrls.find_one({"oobid": oobid},sort=[('date', -1)])
    return short_url

def store_short_url(short_url):
    db.shortUrls.insert_one(short_url)

def expire_short_url(oobid):
        # TODO order by date
        db.shortUrls.update_one(
            {"oobid": oobid}, {
                "$set": {
                            "expires_time": int(0)
                        }
            }
        )
    