import os
import json
import requests
import base64
import sys
import time
import magic
import gzip

oid = sys.argv[1]
sid = sys.argv[2]
payload_id = sys.argv[3]
payload_type = sys.argv[4]
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


def get_artifact(payload_type, oid, artifact_id):
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

    # if this is a small artifact, we can just grab the payload base64 contents
    try:
        if "/" in json.loads(response.text)["path"]:
            return (
                "base64",
                json.loads(response.text)["payload"],
                json.loads(response.text)["path"].split("/")[-1],
            )
        else:
            return (
                "base64",
                json.loads(response.text)["payload"],
                json.loads(response.text)["path"].split("\\")[-1],
            )

    # hayabusa/plaso/large triage artifacts get exported to google storage, so we will retrieve the url from the export param
    except:
        return (
            "export",
            json.loads(response.text)["export"],
            json.loads(response.text)["path"].split("\\")[-1],
        )


def get_ext_artifact(oid, artifact_id):
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

    # if this is a small artifact, we can just grab the payload base64 contents
    try:
        return "payload", json.loads(response.text)["payload"]
    # larger artifacts get exported to google storage, so we will retrieve the url from the export param
    except:
        return "export", json.loads(response.text)["export"]


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
    with open(
        "/opt/timesketch/upload/%s_%s_%s.gz"
        % (get_sensor(sid)["info"]["hostname"], oid, file_name),
        "wb",
    ) as fh:
        fh.write(base64.decodebytes(b64_string.encode() + b"=="))

    return "%s_%s_%s.gz" % (get_sensor(sid)["info"]["hostname"], oid, file_name)


def convert_and_save_hayabusa(b64_string, payload_id):
    with open("/opt/timesketch/upload/%s_%s.csv" % (oid, payload_id), "wb") as fh:
        fh.write(base64.decodebytes(b64_string.encode() + b"=="))

    file_type = magic.from_file("/opt/timesketch/upload/%s_%s.csv" % (oid, payload_id))

    if "CSV" not in file_type:
        with gzip.open(
            "/opt/timesketch/upload/%s_%s.csv" % (oid, payload_id), "rb"
        ) as file:
            contents = file.read()
        with open("/opt/timesketch/upload/%s_%s.csv" % (oid, payload_id), "wb") as fh:
            fh.write(contents)

    return "%s_%s.csv" % (oid, payload_id)


def convert_and_save_plaso(b64_string, payload_id):
    with open("/opt/timesketch/upload/%s_%s.plaso" % (oid, payload_id), "wb") as fh:
        fh.write(base64.decodebytes(b64_string.encode() + b"=="))

    return "%s_%s.plaso" % (oid, payload_id)


def download_file(url, file_name):
    filename = "/opt/timesketch/upload/%s_%s_%s" % (
        get_sensor(sid)["info"]["hostname"],
        oid,
        file_name,
    )

    while True:
        response = requests.head(url=url)
        if response.status_code == 200:
            break
        else:
            time.sleep(5)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as localfile:
            for chunk in r.iter_content(chunk_size=8192): 
                localfile.write(chunk)

    return "%s_%s_%s" % (get_sensor(sid)["info"]["hostname"], oid, file_name)


def download_plaso(url, payload_id):
    filename = "/opt/timesketch/upload/%s_%s.plaso" % (oid, payload_id)

    while True:
        response = requests.head(url=url)
        if response.status_code == 200:
            break
        else:
            time.sleep(5)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as localfile:
            for chunk in r.iter_content(chunk_size=8192): 
                localfile.write(chunk)

    return "%s_%s.plaso" % (oid, payload_id)


def download_hayabusa(url, payload_id):
    filename = "/opt/timesketch/upload/%s_%s.csv" % (oid, payload_id)

    while True:
        response = requests.head(url=url)
        if response.status_code == 200:
            break
        else:
            time.sleep(5)

    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as localfile:
            for chunk in r.iter_content(chunk_size=8192): 
                localfile.write(chunk)

    return "%s_%s.csv" % (oid, payload_id)


if payload_type == "hayabusa":
    # process hayabusa csv

    # get artifact from LC
    export_type, artifact = get_ext_artifact(oid, payload_id)
    if export_type == "payload":
        print(convert_and_save_hayabusa(artifact, payload_id))
    else:
        print(download_hayabusa(artifact, payload_id))

elif payload_type == "plaso":
    # process plaso file

    # get artifact from LC
    export_type, artifact = get_ext_artifact(oid, payload_id)
    if export_type == "payload":
        print(convert_and_save_plaso(artifact, payload_id))
    else:
        print(download_plaso(artifact, payload_id))

else:
    # process raw triage file

    # get artifact from LC
    artifact_type, artifact, file_name = get_artifact(payload_type, oid, payload_id)

    # if base64 artifact, convert and save gz file
    if artifact_type == "base64":
        print(convert_and_save(artifact, file_name))
    # otherwise, download from google storage and process files in timesketch
    else:
        time.sleep(20)
        print(download_file(artifact, file_name))
