""" DIDComm v2 Mediator """
import datetime
import uvicorn
from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from didcomm.unpack import unpack
from didcomm.common.resolvers import ResolversConfig
from didcomm_v2.peer_did import create_peer_did
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm_v2.message_routing import message_routing
from protocols.oob import create_oob
from db_utils import get_oob_did, store_oob_did

app = FastAPI()
SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000
PUBLIC_URL = "https://mediator.rootsid.cloud"
secrets_resolver = get_secret_resolver()
app.state.oob_did = None
app.state.oob_url = None

@app.on_event("startup")
async def startup():
    """ Server start up """
    oob = get_oob_did()
    if not oob:
        app.state.oob_did = await create_peer_did(1, 1, service_endpoint="http://127.0.0.1:8000")
        store_oob_did({
          "did": app.state.oob_did,
          "date": int(datetime.datetime.now().timestamp())*1000,
          "url": PUBLIC_URL
        })
    else:
        app.state.oob_did = oob["did"]

    print(app.state.oob_did)
    app.state.oob_url = create_oob(app.state.oob_did, PUBLIC_URL)
    print(app.state.oob_url)


@app.post("/", status_code=202)
async def receive_message(request: Request):
    """ Endpoint for receiving all DIDComm messages """
    try:
        unpack_msg = await unpack(
            resolvers_config=ResolversConfig(
                secrets_resolver=secrets_resolver,
                did_resolver=DIDResolverPeerDID()
            ),
            packed_msg=await request.json()
        )
        print(unpack_msg)
    # FIXME REPORT PROBLEM
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=400, detail='Malformed Message')
    else:
        print(unpack_msg.message.type)
        return await message_routing(unpack_msg)

            # if {"return_route": "all"} in unpack_msg.message.custom_headers 
            # or {"return_route": "thread"} in unpack_msg.message.custom_headers:
            #   print("response inline")
            #   return response_packed.packed_msg
            # else:
            #   print("send in another thread")


@app.get("/oob_qrcode")
async def get_oob_qrcode():
    ''' Return OOB QR Code image '''
    return FileResponse("oob_qrcode.png")


@app.get("/oob_url")
async def get_oob_url():
    ''' Return OOB URL '''
    return Response(app.state.oob_url)

if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_IP, port=SERVER_PORT, reload=True)
