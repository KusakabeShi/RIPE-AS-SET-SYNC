#!/usr/bin/python3
import os
from ripe_asset_sync import RipeAsSetClient, load_clients, extract_client_as_sets, flatten_as_sets

as_set = os.environ["AS_SET"]
ars_client_path = os.environ["ARS_CLIENTS_PATH"]
max_asset_len = int(os.environ.get("MAX_ASSET_LEN", 3000))

clients = load_clients(ars_client_path)
as_sets_by_asn = extract_client_as_sets(clients)
members = flatten_as_sets(as_sets_by_asn)

with RipeAsSetClient(
    as_set_name=as_set,
    cert_pem=os.environ["RIPE_CLIENT_CERT"],
    key_pem=os.environ["RIPE_CLIENT_KEY"],
    cache_dir="/root/arouteserver/cache",
    max_asset_len=max_asset_len,
) as client:
    client.sync_members(members)
