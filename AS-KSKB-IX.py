#!/usr/bin/python3
import requests
import json
import yaml
import os
from pathlib import Path

as_set = os.environ["AS_SET"]
password = os.environ["RIPE_PASSWD"]

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

client_list = yaml.safe_load(open("/root/arouteserver/clients.yml").read())["clients"]
client_as_set = [(c["asn"],c["cfg"]["filtering"]["irrdb"]["as_sets"]) for c in client_list]
client_as_set = {c[0]:c[1] if c[1] != [] else ["AS" + str(c[0])] for c in client_as_set}
ixmember_new = sum(list(client_as_set.values()), [])
ixmember_new = {sa:"" for sa in ixmember_new}
ixmember_new = [member if not member.startswith("RIPE:") else member[6:] for member in ixmember_new.keys()]

if ixmember_old != ixmember_new:
    new_json = pack_member(base_json_old,ixmember_new)
    payload = json.dumps(new_json)
    response = requests.request("PUT", url, headers=headers, data=payload)
    response.raise_for_status()
    base_json_new = json.loads(response.text)
else:
    print("same, no update")

open(base_json_save,"w").write(json.dumps(base_json_new))