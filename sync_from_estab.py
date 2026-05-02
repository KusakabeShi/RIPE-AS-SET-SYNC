#!/usr/bin/python3
import os
import yaml
import argparse
from ripe_asset_sync import RipeAsSetClient

as_set = os.environ["AS_SET"]
client_asset_path = os.environ["CLIENTS_ASSET_PATH"]
max_asset_len = int(os.environ.get("MAX_ASSET_LEN", 3000))

parser = argparse.ArgumentParser()
parser.add_argument("--flat", help="Flat the asset", action="store_true")
args = parser.parse_args()

data = yaml.safe_load(open(client_asset_path).read())
if not args.flat:
    members = data["all"]["as-set"]
else:
    members = ["AS" + str(x) for x in data["all"]["as-set-flat"]]

members = [m.split("::")[1] if "::" in m else m for m in members]

with RipeAsSetClient(
    as_set_name=as_set,
    cert_pem=os.environ["RIPE_CLIENT_CERT"],
    key_pem=os.environ["RIPE_CLIENT_KEY"],
    cache_dir="/root/arouteserver/cache",
    max_asset_len=max_asset_len,
) as client:
    client.sync_members(members)
