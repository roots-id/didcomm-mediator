""" DIDComm v2 Mediator """
import datetime
import uvicorn
from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response, RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from didcomm.unpack import unpack
from didcomm.common.resolvers import ResolversConfig
from didcomm_v2.peer_did import create_peer_did
from didcomm_v2.peer_did import get_secret_resolver
from didcomm_v2.peer_did import DIDResolverPeerDID
from didcomm_v2.message_dispatch import message_dispatch
from protocols.oob import create_oob
from db_utils import get_oob_did, store_oob_did, get_short_url
import os
import json

app = FastAPI()
SERVER_IP = "0.0.0.0"
SERVER_PORT = 8000
PUBLIC_URL = os.environ["PUBLIC_URL"] if "PUBLIC_URL" in os.environ  else "http://127.0.0.1:8000"
secrets_resolver = get_secret_resolver()
app.state.oob_did = None
app.state.oob_url = None
app.state.invitation_url = None

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """ Server start up """
    print("Server Start up")
    oob = get_oob_did()
    print(oob)
    if not oob or os.environ["ROTATE_OOB"]=="1":
        print("Generating OOB")
        app.state.oob_did = await create_peer_did(1, 1, service_endpoint=PUBLIC_URL)
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
    # FIXME REPORT PROBLEM
    except Exception as ex:
        print(ex)
        raise HTTPException(status_code=400, detail=str(ex))
    else:
        print(unpack_msg.message.type)
        resp = await message_dispatch(unpack_msg)
        if resp:
            return json.loads(resp)
        else:
            return
        

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

@app.get("/oob_small_qrcode")
async def get_oob_short_qrcode():
    ''' Return Short OOB QR Code image '''
    return FileResponse("oob_small_qrcode.png")

@app.get("/oob_url")
async def get_oob_url():
    ''' Return OOB URL '''
    return Response(app.state.oob_url)


@app.get("/qr")
async def redirect_shortened_url(_oobid):
    ''' Redirect short URLs '''
    print(_oobid)
    short_url_reg = get_short_url(_oobid)
    if short_url_reg and (short_url_reg["expires_time"] > int(datetime.datetime.now().timestamp()*1000) or short_url_reg["expires_time"] == 0):
        print(short_url_reg["long_url"])
        return RedirectResponse(short_url_reg["long_url"], 301)
    else:
        raise HTTPException(status_code=404)

@app.get("/qr/{path}")
async def redirect_shortened_url(_oobid):
    ''' Redirect short URLs '''
    print(_oobid)
    short_url_reg = get_short_url(_oobid)
    if short_url_reg and short_url_reg["expires_time"] > int(datetime.datetime.now().timestamp()*1000):
        print(short_url_reg["long_url"])
        return RedirectResponse(short_url_reg["long_url"], 301)
    else:
        raise HTTPException(status_code=404)


@app.get("/")
def index():
    with open('web/index.html') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/rootsIdLogo")
async def get_oob_short_qrcode():
    ''' Return RootsID Logo '''
    return FileResponse("web/rootsIdLogo.png")

if __name__ == "__main__":
    uvicorn.run("main:app", host=SERVER_IP, port=SERVER_PORT, reload=True)


