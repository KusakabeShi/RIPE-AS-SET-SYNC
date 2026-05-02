import copy
import json
import os
import tempfile

import requests
from pathlib import Path


def _extract_member(base_json):
    return [
        a["value"]
        for a in base_json["objects"]["object"][0]["attributes"]["attribute"]
        if a["name"] == "members"
    ]


def _index_of_first(lst, pred):
    for i, v in enumerate(lst):
        if pred(v):
            return i
    return 1


def _pack_member(base_json, member_list):
    base_json = copy.deepcopy(base_json)
    old_list = base_json["objects"]["object"][0]["attributes"]["attribute"]
    first_member_idx = _index_of_first(old_list, lambda x: x["name"] == "members")
    old_list = [a for a in old_list if a["name"] != "members"]
    new_members = [
        {
            "name": "members",
            "value": member,
            "referenced-type": "aut-num" if member[:2] == "AS" and member[2:].isdecimal() else "as-set",
        }
        for member in member_list
    ]
    new_list = old_list[:first_member_idx] + new_members + old_list[first_member_idx:]
    for item in new_list:
        item.pop("comment", None)
    base_json["objects"]["object"][0]["attributes"]["attribute"] = new_list
    return base_json


class RipeAsSetClient:
    """Client for RIPE REST API as-set management with X.509 certificate auth."""

    def __init__(self, as_set_name, cert_pem, key_pem, cache_dir=".", max_asset_len=3000):
        self.as_set_name = as_set_name
        self.max_asset_len = max_asset_len
        self.cache_path = Path(cache_dir) / (as_set_name + "_last.json")
        self.url = f"https://rest-cert.db.ripe.net/ripe/as-set/{as_set_name}"
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}

        self._cert_f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
        self._key_f = tempfile.NamedTemporaryFile(mode="w", suffix=".pem", delete=False)
        self._cert_f.write(cert_pem)
        self._key_f.write(key_pem)
        self._cert_f.close()
        self._key_f.close()
        self._cert = (self._cert_f.name, self._key_f.name)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        for f in (self._cert_f.name, self._key_f.name):
            try:
                os.unlink(f)
            except OSError:
                pass

    def _fetch_from_ripe(self):
        resp = requests.get(self.url, headers=self.headers, cert=self._cert)
        resp.raise_for_status()
        return resp.json()

    def get_current_state(self):
        """Fetch current as-set JSON from cache or RIPE."""
        if self.cache_path.is_file():
            return json.loads(self.cache_path.read_text())
        return self._fetch_from_ripe()

    def get_current_members(self):
        """Return current member list."""
        return _extract_member(self.get_current_state())

    def sync_members(self, new_members, dry_run=False):
        """Sync the as-set to contain exactly new_members.

        Returns True if an update was performed, False if already in sync.
        """
        if len(new_members) > self.max_asset_len:
            raise ValueError(
                f"AS-Set length: {len(new_members)}, exceeds MAX_ASSET_LEN: {self.max_asset_len}"
            )

        base_json = self.get_current_state()
        old_members = _extract_member(base_json)

        if old_members == list(new_members):
            print("same, no update:", self.as_set_name)
            self._save_cache(base_json)
            return False

        new_json = _pack_member(base_json, new_members)
        if dry_run:
            print("dry run, would update:", self.as_set_name)
            return True

        resp = requests.put(
            self.url, headers=self.headers, data=json.dumps(new_json), cert=self._cert
        )
        resp.raise_for_status()
        result_json = resp.json()
        self._save_cache(result_json)
        print("updated:", self.as_set_name)
        return True

    def _save_cache(self, data):
        self.cache_path.write_text(json.dumps(data))
