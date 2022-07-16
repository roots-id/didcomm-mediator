## DIDComm Mediator v2

As a general principle, the Mediator implements latest specifications and protocols from [DIF](https://identity.foundation) and [Aries Interoperability Profiles](https://github.com/hyperledger/aries-rfcs/blob/main/concepts/0302-aries-interop-profile/README.md), in particular:
* [DIF DIDComm Messaging V2](https://identity.foundation/didcomm-messaging/spec/)
* [Aries RFC 0434: Out-of-Band Protocol 1.1](https://github.com/hyperledger/aries-rfcs/tree/bed4989dd6517f7a9de3696800e57e4c6ef49231/features/0434-outofband)
* ~~[Aries RFC 0160: Connection Protocol](https://github.com/hyperledger/aries-rfcs/blob/main/features/0160-connection-protocol/README.md)~~  replaced by Aries RFC 0023
* ~~[Aries RFC 0023: DID Exchange Protocol 1.0](https://github.com/hyperledger/aries-rfcs/tree/b3a3942ef052039e73cd23d847f42947f8287da2/features/0023-did-exchange)~~ not needed in DIDComm v2
* [Aries RFC 0211: Mediator Coordination Protocol](https://github.com/hyperledger/aries-rfcs/tree/b3a3942ef052039e73cd23d847f42947f8287da2/features/0211-route-coordination) --> Publishing v2
* [DIDComm v2 Return-Route Extension](https://github.com/decentralized-identity/didcomm-messaging/blob/main/extensions/return_route/main.md)
* [Aries RFC 0212: Pickup Protocol 2.0](https://github.com/hyperledger/aries-rfcs/blob/cab12f80217ab3aab6243e69051c3442a62a0b45/features/0685-pickup-v2/README.md) --> Publishing v3
* [Peer DID Method Specification](https://identity.foundation/peer-did-method-spec/)

The initial implementation uses HTTPS transport with [Transport Return Route](https://github.com/hyperledger/aries-rfcs/blob/main/features/0092-transport-return-route/README.md), meaning that the mobile user sends messages to the mediator as HTTPS POST requests, and receives a message back from the mediator in the HTTPS response body.
Additionally, the [Pickup Protocol](https://github.com/hyperledger/aries-rfcs/blob/cab12f80217ab3aab6243e69051c3442a62a0b45/features/0685-pickup-v2/README.md) is implemented so mobile users can retrieve pending messages from the mediator asynchronously.
Future releases will implement a websocket transport with [Live Mode](https://github.com/hyperledger/aries-rfcs/blob/cab12f80217ab3aab6243e69051c3442a62a0b45/features/0685-pickup-v2/README.md#live-mode) capability that adds a better realtime communication when both parties are online.

### Significant libraries
DIDComm and Peer DID is provided by the following libraries:
* [sicpa-dlab/didcomm-python](https://github.com/sicpa-dlab/didcomm-python)
* [sicpa-dlab/peer-did-python](https://github.com/sicpa-dlab/peer-did-python)


### Installation
```
python -m venv ./venv 
source ./venv/bin/activate
pip install requirements.txt
```

### Run
`uvicorn main:app --reload`

### Build and docker
```
docker build -f ./docker/Dockerfile . --platform=linux/amd64 -t rodopincha/didcomm-mediator
docker run -p 8000:8000 rodopincha/didcomm-mediator
```

### Process Overview (need to be updated!)
In the following process Alice(A) wants to invite Bob(B) to create a connection by exchanging DID (did:peer). Since A is a mobile user and can't provide a direct link to communicate, she will use a mediator(M) as a means to be reached out. B may or may not  need a mediator, but if that is the case, the mediator can be the same (M) or another.
The process below includes as reference the **_@type_** of the message as defined in Aries protocols.
1. Initially, **A** needs to connect with **M**, so **M** provides to **A** an out-of-band invitation in an URL or QR code stating a connection URL in `serviceEndoint` and a did:peer in`recipientKeys` ("@type": "https://didcomm.org/out-of-band/%VER/invitation"). Note that this did:peer is a general invite DID used only for initial communication set up.
2. **A** creates a dedicated did:peer to connect to **M** `A.didpeer@A:M`.
3. **A** generates a _request_ messsage ("@type": "https://didcomm.org/didexchange/1.0/request") providing her DID documment for key `A.didpeer@A:M`. The message is encrypted with **M** invitation keys and POSTed to the URL obteined in `serviceEndpoint`
4. **M** creates a dedicated did:peer to connect to **A** `M.didpeer@M:A`
5. **M** responds the received http POST message with a _response_ message ("@type": "https://didcomm.org/didexchange/1.0/response") providing the DID documment  for `M.didpeer@M:A`. Message is incrypted for `A.didpeer@A:M`
6. To conlcude the communication setup, **A** sends a _complete_ message to **M**  ("@type": "https://didcomm.org/didexchange/1.0/complete"), that M responds with 200 success. This final message is still encrypted with **M**'s invitation keys. Subsecuent communication will use `M.didpeer@M:A` and `A.didpeer@A:M`.
7. Now **A** starts a mediation request  by POSTing a _mediate-request_ message ("@type": "https://didcomm.org/coordinate-mediation/1.0//mediate-request")  to **M**, which is replied with a _mediate-grant_ message("@type": "https://didcomm.org/coordinate-mediation/1.0//mediate-grant"). Messages are encrypted with `A.didpeer@A:M` and `M.didpeer@M:A`. The _mediate-grant_ message provides the `endpoint` and `routing-keys` needed by B (TODO: check if routing-keys are per _mediate-grant_ or per user)
8. **A** creates a did:peer to invite **B** `A.didpeer@Ainvite:B`
9. **A** updates the list of recipient keys in **M** by POSTing  a _keylist-update_ message to **M** ("@type": "https://didcomm.org/coordinate-mediation/1.0//keylist-update") including `A.didpeer@Ainvite:B`
10. **M** responds _the keylist-update_ with a _keylist-update-response_ message("@type": "https://didcomm.org/coordinate-mediation/1.0//keylist-update-response") 
11. **A** creates an _out-of-band_ inviation with mediator `endpoint` and `routing-keys`, and `A.didpeer@A:B` in `recipientKeys` ("@type": "https://didcomm.org/out-of-band/%VER/invitation"). **B** gets this message as a QR code or URL 
12. **B** creates a dedicated did:peer to communicate with **A** `B.didpeer@B:A`
13. **B** creates a _request_ messsage ("@type": "https://didcomm.org/didexchange/1.0/request") providing `B.didpeer@B:A` DID document. He may also needs to add a `serviceEndpoint` and/or `routing-keys` if using also a mediator. The message is encrypted with `A.didpeer@Ainvite:B` keys.
14. **B** wraps the message in a _Forward_ message ("type": "https://didcomm.org/routing/2.0/forward") and encrypts with **M** `routing-keys`
15. **B** POST the message to **M** at `endpoint` defined in the _out-of-band_ invitation
16. **M** unpacks the _forward_ message, inspects the `to` field, looks up keys in its DB and stores the message as pending delivery for **A**
17. Asynchronously, **A** checks with **M** if there're pending messsages by POSTing to **M** a _status-request_ ("@type": "https://didcomm.org/messagepickup/2.0/status-request") that is replied with the _status_ message ("@type": "https://didcomm.org/messagepickup/2.0/status")
18. If there're pending messages, **A** POST a _delivery-request_ message to **M** ("@type": "https://didcomm.org/messagepickup/2.0/delivery-request") that is responded with the _delivery_ message ("@type": "https://didcomm.org/messagepickup/2.0/delivery") that includes message from **B**.
19. **A** finalizes the message pickup with a _messages-received_ message ("@type": "https://didcomm.org/messagepickup/2.0/messages-received")
20. After receiving the connection request from **B**, **A** generates a new dedicated did:peer to connect with **B** `A.didpeer@A:B`.
21. **A** updates the list of recipient keys in **M** by POSTing  a _keylist-update_ message to **M** ("@type": "https://didcomm.org/coordinate-mediation/1.0//keylist-update") including `A.didpeer@A:B` and removing`A.didpeer@Ainvite:B`.
22. **A** creates a _response_ message ("@type": "https://didcomm.org/didexchange/1.0/response") including her DID documment with  key `A.didpeer@A:B`, mediator's routing key, and mediator's endpoint in `serviceEndpoint`. Message is encrypted for `B.didpeer@B:A`
23. **A** sends the message to **B** using **B** `serviceEndpoint` or `routing-keys`. That process may require a mediator as well, that can be same mediator or another.
24. **B** sends the _complete_ message to finalize communication setup and wrap it in a _Forward_ message as before.
25. **A** receives the complete message from the mediator by quering **M** for message pickup as before
26. **A** and **B** are now ready to communicate

NOTE: all post message from A will have the decorator for `Transports Return Route`

## Build and docker
```
docker build -f ./docker/Dockerfile . --platform=linux/amd64 -t rodopincha/didcomm-mediator
docker run -p 8000:8000 rodopincha/didcomm-mediator
```
