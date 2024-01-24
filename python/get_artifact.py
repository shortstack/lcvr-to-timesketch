
import os 
import json 
import requests 
import base64
import sys 
import time 


oid = sys.argv[1]
sid = sys.argv[2]
payload_id = sys.argv[3]
api_key = os.getenv("LC_API_KEY")
uid = os.getenv("LC_UID")


def generate_org_jwt(oid):
    base_url = "https://jwt.limacharlie.io"

    url = "%s?uid=%s&secret=%s&oid=%s" % (base_url, uid, api_key, oid)

    try:
        r = requests.get(url)
        jwt = r.json()["jwt"]
        return jwt

    except:
        return ""


def get_artifact(oid, artifact_id):
    url = "%s/v1/insight/%s/artifacts/originals/%s" % (
        "https://api.limacharlie.io",
        oid,
        artifact_id,
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % (generate_org_jwt(oid)),
    }

    response = requests.request("GET", url, headers=headers)

    # if this is a small/non triage artifact, we can just grab the payload base64 contents
    try:
        if "/" in json.loads(response.text)["path"]:
            return "base64", json.loads(response.text)["payload"], json.loads(response.text)["path"].split("/")[-1]
        else:
            return "base64", json.loads(response.text)["payload"], json.loads(response.text)["path"].split("\\")[-1]
    # triage artifacts get exported to google storage, so we will retrieve the url from the export param
    except:
        return "export", json.loads(response.text)["export"], json.loads(response.text)["path"].split("\\")[-1]


def get_sensor(sid):
    url = "%s/v1/%s" % (
        "https://api.limacharlie.io",
        sid,
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer %s" % (generate_org_jwt(oid)),
    }

    response = requests.request("GET", url, headers=headers)

    return json.loads(response.text)


def convert_and_save(b64_string, file_name):

    with open("/opt/timesketch/upload/%s_%s_%s.gz" % (get_sensor(sid)["info"]["hostname"], oid, file_name), "wb") as fh:
        fh.write(base64.decodebytes(b64_string.encode() + b"=="))

    return "%s_%s_%s.gz" % (get_sensor(sid)["info"]["hostname"], oid, file_name)


def download_file(url, file_name):
    
    filename = "/opt/timesketch/upload/%s_%s_%s" % (get_sensor(sid)["info"]["hostname"], oid, file_name)

    response = requests.request("GET", url=url)

    with open(filename, mode='wb') as localfile:
        localfile.write(response.content)

    return "%s_%s_%s" % (get_sensor(sid)["info"]["hostname"], oid, file_name)


# get artifact from LC
artifact_type, artifact, file_name = get_artifact(oid, payload_id)

# if base64 artifact, convert and save gz file
if artifact_type == "base64":
    print(convert_and_save(artifact, file_name))
# otherwise, download from google storage and process files in timesketch
else:
    time.sleep(10)
    print(download_file(artifact, file_name))
