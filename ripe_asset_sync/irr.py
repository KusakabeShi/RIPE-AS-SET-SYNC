import json
import os
import subprocess
import time

T1_ASNS = [
    701, 1239, 1299, 2914, 3257, 3320, 3356, 3491, 5511, 6453,
    6461, 6762, 6830, 7018, 12956, 174, 1273, 2828, 4134, 4809,
    4637, 6939, 7473, 7922, 9002,
]

DEFAULT_SOURCES = "RIPE,APNIC,AFRINIC,ARIN,NTTCOM,ALTDB,BBOI,BELL,JPIRR,LEVEL3,RADB,TC"


class IrrCache:
    """Cached bgpq4 IRR query wrapper."""

    def __init__(self, cache_path, expire=86400, default_sources=DEFAULT_SOURCES, t1_asns=None):
        self.cache_path = cache_path
        self.expire = expire
        self.default_sources = default_sources
        self.t1_asns = t1_asns if t1_asns is not None else T1_ASNS
        self._cache = {}
        if os.path.isfile(cache_path):
            try:
                self._cache = json.loads(open(cache_path).read())
            except Exception:
                self._cache = {}

    def query(self, as_set_all, af=6):
        """Query IRR for an as-set. Returns dict with keys: ASNs, prefix_num, time, t1_asns."""
        if as_set_all in self._cache and (self._cache[as_set_all]["time"] + self.expire) > time.time():
            return self._cache[as_set_all]

        sources = self.default_sources
        as_set = as_set_all
        if "::" in as_set_all:
            sources, as_set = as_set.split("::")

        bgpq4_out = subprocess.run(
            ["bgpq4", "-" + str(af), "-b", "-R", "48", "-S", sources, "-m", "48", as_set],
            stdout=subprocess.PIPE,
        )
        bgpq4_asns = subprocess.run(
            ["bgpq4", "-" + str(af), "-tj", "-S", sources, as_set],
            stdout=subprocess.PIPE,
        ).stdout.decode()
        asset_asns = json.loads(bgpq4_asns)["NN"]

        entry = {
            "ASNs": asset_asns,
            "prefix_num": max(0, len(bgpq4_out.stdout.decode().split("\n")) - 2),
            "time": time.time(),
            "t1_asns": sorted(set(asset_asns) & set(self.t1_asns)),
        }
        self._cache[as_set_all] = entry
        return entry

    def get(self, as_set_all):
        """Get cached entry without querying. Returns None if not cached."""
        return self._cache.get(as_set_all)

    def save(self):
        """Persist cache to disk."""
        open(self.cache_path, "w").write(json.dumps(self._cache, indent=4))
