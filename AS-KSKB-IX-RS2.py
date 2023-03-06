#!/usr/bin/python3
import requests
import json
import yaml
import ipaddress
import sys
import os
import argparse
from subprocess import PIPE, Popen
from pathlib import Path

as_set = os.environ["AS_SET"]
password = os.environ["RIPE_PASSWD"]
client_asset_path = os.environ["CLIENTS_ASSET_PATH"]


parser = argparse.ArgumentParser()
parser.add_argument("--flat", help="Flat the asset",action="store_true")
args = parser.parse_args()

url = f"https://rest.db.ripe.net/ripe/as-set/{as_set}?password={password}"

headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

def extract_member(base_json):
    return list(map(lambda x:x["value"],filter(lambda x:x["name"] == "members", base_json["objects"]["object"][0]["attributes"]["attribute"])))
def pack_member(base_json,member_list):
    atlist = base_json["objects"]["object"][0]["attributes"]["attribute"]
    atlist = list(filter(lambda x:x["name"] != "members",atlist))
    atlist = atlist[0:3] + [{"name": "members", "value": member, "referenced-type":"aut-num" if member[:2] == "AS" and member[2:].isdecimal() else "as-set" } for member in member_list] + atlist[3:]
    base_json["objects"]["object"][0]["attributes"]["attribute"] = atlist
    return base_json


base_json_save = Path(as_set + "_last.json")
if base_json_save.is_file():
    base_json_old = json.loads(open(base_json_save).read())
else:
    base_json_old = json.loads(requests.request("GET", url, headers=headers).text)
    
base_json_new = base_json_old
ixmember_old = extract_member(base_json_old)
if not args.flat:
    client_as_set = yaml.safe_load(open(client_asset_path).read())["all"]["as-set"]
else:
    client_as_set = yaml.safe_load(open(client_asset_path).read())["all"]["as-set-flat"]
    client_as_set = list(map(lambda x:"AS" + str(x),client_as_set))
ixmember_new = [member if not "::" in member else member.split("::")[1] for member in client_as_set]

if ixmember_old != ixmember_new:
    new_json = pack_member(base_json_old,ixmember_new)
    payload = json.dumps(new_json)
    response = requests.request("PUT", url, headers=headers, data=payload)
    response.raise_for_status()
    base_json_new = json.loads(response.text)
    print("updated:",as_set)
else:
    print("same, no update:",as_set)

open(base_json_save,"w").write(json.dumps(base_json_new))
