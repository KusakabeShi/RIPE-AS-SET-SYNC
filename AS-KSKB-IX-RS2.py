#!/usr/bin/python3
import requests
import json
import yaml
import ipaddress
import sys
from subprocess import PIPE, Popen
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
def getval(strin):
    return strin.split(":",1)[1].strip()
    
def getAddr(addr):
    addr = addr.strip()
    if "%" in addr:
        addr = addr.split("%",1)
    else:
        addr = addr, None
    return ipaddress.ip_address(addr[0]) , addr[1]
    
def getAddrFromChannel(birdspaline):
    birdspaline = birdspaline.strip()
    if " " in birdspaline:
        addr,ll = birdspaline.split(" ",1)
        if addr == "::":
            return ipaddress.ip_address(ll)
        return ipaddress.ip_address(addr)
    return ipaddress.ip_address(birdspaline)
    
def getroutecount(birdspaline):
    birdspaline = birdspaline.strip()
    infos_list = list( map( lambda x:x.strip(), birdspaline.split(",")))
    infos =  {"imported": None,"filtered":None,"exported": None,"preferred": None}
    for info in infos_list:
        val,key = info.strip().split(" ")
        val = int(val)
        infos[key] = val
    return infos
    
def get_bird_session(n="*",birdc_output = None):
    if n == "*":
        n = '"*"'
    if birdc_output == None:
        birdc_output = Popen(["birdc", "s", "p","a",n], stdin=PIPE, stdout=PIPE).communicate()[0].decode()
    birdc_output = birdc_output.split("\n")[2:]
    birdc_output = "\n".join(birdc_output).split("\n\n")
    result_list = []
    for proto_str in birdc_output:
        proto_str_line = proto_str.split("\n")
        protoinfo = proto_str_line[0].strip().split(" ")
        if len(protoinfo) < 3:
            continue
        proto_name, proto_type, remain = protoinfo[0] , protoinfo[1], protoinfo[2:]
        if proto_type != "BGP":
            continue
        result = {"name": proto_name, "state":None, "as": {"local":0, "remote":0}, "addr":{"af": 0, "local":None, "remote":None, "interface":None}, "route":{"ipv4":{"imported":0,"exported":0,"preferred":0},"ipv6":{"imported":0,"exported":0,"preferred":0}}}
        current_channel = ""
        for L in proto_str_line:
            if "BGP state:" in L:
                result["state"] = getval(L)
            elif "Neighbor AS:" in L:
                result["as"]["remote"] = int(getval(L))
            elif "Local AS" in L:
                result["as"]["local"] = int(getval(L))
            elif "Neighbor address:" in L:
                remote = getval(L)
                addrobj,interface = getAddr(remote)
                result["addr"]["interface"] = interface
                result["addr"]["remote"] = str(addrobj)
                if type(addrobj) == ipaddress.IPv4Address:
                    result["addr"]["af"] = 4
                elif type(addrobj) == ipaddress.IPv6Address:
                    result["addr"]["af"] = 6
            elif "Channel" in L:
                current_channel = L.split("Channel ")[1].strip()
            elif "Routes:" in L:
                result["route"][current_channel] = getroutecount(getval(L))
            elif "BGP Next hop:" in L:
                if (result["addr"]["af"] == 4 and current_channel == "ipv4") or (result["addr"]["af"] == 6 and current_channel == "ipv6"):
                    result["addr"]["local"] = str(getAddrFromChannel(getval(L)))
        result_list += [result]
    #return yaml.safe_dump(result_list)
    return result_list


base_json_save = Path(as_set + "_last.json")
if base_json_save.is_file():
    base_json_old = json.loads(open(base_json_save).read())
else:
    base_json_old = json.loads(requests.request("GET", url, headers=headers).text)
    
base_json_new = base_json_old
ixmember_old = extract_member(base_json_old)

bird_conninfo = get_bird_session("*")
estab_sess = set(map(lambda x:x["as"]["remote"],filter(lambda x:x["state"] == "Established",bird_conninfo)))

client_list = yaml.safe_load(open("/root/arouteserver/clients.yml").read())["clients"]
client_as_set = [(c["asn"],c["cfg"]["filtering"]["irrdb"]["as_sets"]) for c in client_list]
client_as_set = list(filter(lambda x:x[0] in estab_sess,client_as_set))
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