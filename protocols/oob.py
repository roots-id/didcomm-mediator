""" Out of Band Protocol 2.0 """
import base64
import json
import uuid
import qrcode


def create_oob(did, url):
    """ Create Out of band Message """
    oob_mesage = {
        "type": "https://didcomm.org/out-of-band/2.0/invitation",
        "id": str(uuid.uuid4()),
        "from": did,
        "body": {
            "goal_code": "register",
            "goal": "Register in mediator",
            "accept": [
                "didcomm/v2",
                "didcomm/aip2;env=rfc587"
            ],
        }
    }
    plaintext_ws_removed = json.dumps(oob_mesage).replace(" ", "")
    encoded_plaintextjwm = base64.urlsafe_b64encode(
        plaintext_ws_removed.encode("utf-8"))
    encoded_text = str(encoded_plaintextjwm, "utf-8").replace("=", "")
    oob_url = url + "?_oob=" + encoded_text
    image = qrcode.make(oob_url)
    image.save("oob_qrcode.png")
    return oob_url
