#!/usr/bin/python3
import os
import requests
from ripe_asset_sync import RipeAsSetClient, parse_bird_routes_origin_asns

RS2_route_url = "http://[2404:f4c0:f70e:1980::2:1]:3234/bird?q=show%20route%20where%20%28199594%2C65530%2C7%29%21~bgp_large_community%26%26source%3DRTS_BGP%20all"
route_output = requests.get(RS2_route_url).text
origin_asns = parse_bird_routes_origin_asns(route_output)
members = sorted(["AS" + str(asn) for asn in origin_asns])

with RipeAsSetClient(
    as_set_name=os.environ["AS_SET"],
    cert_pem=os.environ["RIPE_CLIENT_CERT"],
    key_pem=os.environ["RIPE_CLIENT_KEY"],
    cache_dir="/root/arouteserver/cache",
) as client:
    client.sync_members(members)
