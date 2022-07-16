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

def add_mediation():
    return []
def update_keys(remote_did, updates):
    return []
