#!/usr/bin/python3
import requests
import json
import yaml
import ipaddress
import sys
import os
from subprocess import PIPE, Popen
from pathlib import Path

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
        protoinfo = proto_str_line[0].strip().split()
        if len(protoinfo) < 3:
            continue
        proto_name, proto_type, proto_table ,proto_state , proto_since ,proto_info = protoinfo[0] , protoinfo[1], protoinfo[2], protoinfo[3], protoinfo[4], protoinfo[-1]
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