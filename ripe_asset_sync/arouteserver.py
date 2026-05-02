import yaml


def load_clients(path):
    """Load arouteserver clients YAML and return the clients list."""
    return yaml.safe_load(open(path).read())["clients"]


def extract_client_as_sets(clients):
    """Extract {asn: [as-set, ...]} from arouteserver client config.

    If a client has no as_sets configured, defaults to ["AS{asn}"].
    """
    pairs = [(c["asn"], c["cfg"]["filtering"]["irrdb"]["as_sets"]) for c in clients]
    return {asn: (as_sets if as_sets else ["AS" + str(asn)]) for asn, as_sets in pairs}


def flatten_as_sets(as_sets_by_asn, strip_source=True):
    """Flatten all per-ASN as-sets into a deduplicated member list.

    If strip_source is True, removes SOURCE:: prefix (e.g. RIPE::AS-FOO -> AS-FOO).
    """
    all_sets = sum(list(as_sets_by_asn.values()), [])
    seen = {}
    for s in all_sets:
        seen[s] = ""
    members = list(seen.keys())
    if strip_source:
        members = [m.split("::")[1] if "::" in m else m for m in members]
    return members
