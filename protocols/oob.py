""" Out of Band Protocol 2.0 """
import base64
import json
import uuid
import qrcode
from db_utils import store_short_url
import os
import datetime


def create_oob(message, url):
    """ Create Out of band Message """

    plaintext_ws_removed = json.dumps(message).replace(" ", "")
    encoded_plaintextjwm = base64.urlsafe_b64encode(
        plaintext_ws_removed.encode("utf-8"))
    encoded_text = str(encoded_plaintextjwm, "utf-8").replace("=", "")
    oob_url = url + "?_oob=" + encoded_text
    image = qrcode.make(oob_url)
    image.save("oob_qrcode.png")

    #SHORT URL QR CODE
    oobid = str(uuid.uuid4()).replace("-","")
    date = int(datetime.datetime.now().timestamp())*1000
    expires_time = int(date + 315360000)
    short_url = url + "/qr?_oobid=" + oobid
    store_short_url(
            {
                "date": date,
                "expires_time": expires_time,
                "requested_validity_seconds": 315360000,
                "long_url": oob_url,
                "oobid": oobid,
                "short_url_slug": "",
                "goal_code": "shorten.oobv2"
            }
        )
    image_small = qrcode.make(short_url)
    image_small.save("oob_small_qrcode.png")
    return oob_url
