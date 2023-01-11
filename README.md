## RootsID DIDComm v2 Mediator

This Mediator implements the following protocols:

* [DIF DIDComm Messaging V2](https://identity.foundation/didcomm-messaging/spec/)
* [Out-of-Band Messages 2.0](https://identity.foundation/didcomm-messaging/spec/#out-of-band-messages)
* [Routing Protocol 2.0](https://identity.foundation/didcomm-messaging/spec/#routing-protocol-20)
* [DIDComm v2 Return-Route Extension](https://github.com/decentralized-identity/didcomm-messaging/blob/main/extensions/return_route/main.md)
* [Mediator Coordination Protocol 2.0](https://didcomm.org/mediator-coordination/2.0/)
* [Pickup Protocol 3.0](https://didcomm.org/pickup/3.0/): messages processed by this mediator are responded in the same channel (in the response body of the http POST request). It does not enforce the `return_route` header extencion (pending TODO).
* [Peer DID Method Specification](https://identity.foundation/peer-did-method-spec/)
* [HTTPS Transport](https://identity.foundation/didcomm-messaging/spec/#https)

### Extra features
This mediator also implements the following features that can be used as a playground to test other protocols:
* [Trust Ping Protocol 2.0](https://identity.foundation/didcomm-messaging/spec/#trust-ping-protocol-20)
* [Discover Features Protocol 2.0](https://identity.foundation/didcomm-messaging/spec/#discover-features-protocol-20)
* [Basic Message Protocol 2.0](https://didcomm.org/basicmessage/2.0/)
* [Shorten URL Protocol 1.0]()
* [Action Menu Protocol 2.0](https://didcomm.org/action-menu/2.0/)
* [Question Answer Protocol 2.0]()

### ToDo's
Pending features and known issues and missings can be found at the [issues]([issues](https://github.com/roots-id/didcomm-mediator/issues)) section in this repository.
Note that this mediator is currently a **Proof of Concept**. Several `TODO`'s still pending in the code.

### Significant libraries
DIDComm and Peer DID were implemented with the help of the following amazing libraries from SICPA:
* [sicpa-dlab/didcomm-python](https://github.com/sicpa-dlab/didcomm-python)
* [sicpa-dlab/peer-did-python](https://github.com/sicpa-dlab/peer-did-python)

## RootsID Cloud instance live!
We have deployed an instance of the mediator in the cloud for testing, demoing, and learning.
Your identity wallet can scan the following Out of Band invitation QR code and request mediation:

![QR Code](https://mediator.rootsid.cloud/oob_qrcode)

Or scan the small QR code (OOB D) that redirect to the big one:

![Small QR Code](https://mediator.rootsid.cloud/oob_small_qrcode)


### Installation
```
python -m venv ./venv 
source ./venv/bin/activate
pip install requirements.txt
```
### Mongo DB
This mediator use [MongoDB](https://www.mongodb.com) as Data Base. You need to have it installed before running. One installaton option is with docker as:
```
docker pull mongo
docker run --name mongo_example -d mongo
```

### Envirnomental varables
The following environmental variables are needed. Change the values as your need:
```
export DB_URL=mongodb://localhost:27017
export PUBLIC_URL=http://127.0.0.1:8000
export ROTATE_OOB=0  // rotate OOB at startup if set
export MONGODB_USER=XXXXXX
export MONGODB_PASSWORD=yyyyy
export WOLFRAM_ALPHA_API_ID=ZZZZZZ // only for basicmessage demo (https://www.wolframalpha.com)
```

### Runing the agent
```
uvicorn main:app --reload
```

## Testing with Jupyter Notebook
We provide examples of two agents, Alice and Bob, that can send and receive a message routed by the mediator following Mediator Coordination and Pickup Protocols. Code can be found at [sample-notebooks](https://github.com/roots-id/didcomm-mediator/tree/main/sample-notebooks) folder.

### Process Overview (WIP)
In the following process Alice(**A**) wants to invite Bob(B) to create a connection by exchanging DID (did:peer). Since **A** is a mobile user and can't provide a direct link to communicate, she will use a mediator(**M**) as a means to be reached out. **B** may or may not  need a mediator, but if that is the case, the mediator can be the same (**M**) or another.

1. Initially, **A** needs to connect with **M** to request mediation. For that reason **M** provides to **A** (or publicly) an out-of-band invitation in an URL or QR code. The OOB invitation is an unecrypted message with **M**'s public did peer. Let call that DID as `M.public`
2. Now, **A** knows `M.public` DID that she can resolve into a DID Document and get the `serviceEndpoint` of **M**
3. **A** creates a dedicated did:peer to connect to **M**. Let's call it `A.toM` DID.
4. **A** starts a mediation request  by POSTing a `mediate-request` to **M** endpoint. The message will be created from her `A.toM` DID and encrypted to `M.Public`. Additionally, Alice will use the `return-route` extension to receive a message back in the same channel (as a response of the https request).
5. **M** receives and decode the `mediate-request` message, and creates a `request-grant` (or `request-deny`) message. For that message, **M** will create a new DID peer dedicates to the communcations to **A**, lets call it `M.toA` DID. The message will be created from that DID to `A.toM` DID. The mediator will also create a routing DID `M.routing` and will include it in the body of the `mediate-grant` message
6. After receiving the message, Alice can get the routing DID `M.routing`. That DID will be part of her DID Documents as a `serviceEndpont` when communicating with others. That means, that when someone want to send a message to **A**, they will have to route it through the mediator **M**
7. Now Alice is ready to create a DID to communicate to Bob **B**. That DID will include `M.routing` as the `serviceEndopint` URI. Let's call it `A.toB` DID
8. TODO keylist update (I missed that step!)
9. After creating the DID, she can also create an OOB to send to B
10. **B** receives Alices OOB, get `A.toB` DID, and resolving `A.toB` DID Document he is able to get `M.routing`
11. **B** is ready to create a message to Alice ( `A.toB`) using a new DID peer called `B.toA`. The message is encrypted with `A.toB` keys so only Alice can decrypt it.
12. **B** wrap that message as an attachment in a forward message to the mediator `M.routing` DID and send to the Mediator endpoint (the endpoint is obtained from `M.routing` DID)
13. **M** receives the mesagge, get the attachment and keep it for Alice
14. To be continued.....

TODO add flow diagram

## Build docker
```
docker build -f ./Dockerfile .  -t didcomm-mediator // use --platform=linux/amd64 if needed
docker run -p 8000:8000  \
-e DB_URL=mongodb://host.docker.internal:27017 \
-e ROTATE_OOB=0 \
-e PUBLIC_URL=http://localhost:8000 \
didcomm-mediator
```

