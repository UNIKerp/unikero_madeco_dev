import os
import time
import json
import odooly


def new_http_post(url, data, headers={"Content-Type": "application/json"}):
    resp = requests.post(url, data=data, headers=headers)
    try:
        return resp.json()
    except Exception as e:
        return {"error": "{}-{}-{}".format(url, data, str(e))}


def patch_odooly():
    odooly.http_post = new_http_post
