# RIPE-AS-SET-SYNC

Python library and CLI scripts for synchronizing IXP membership to [RIPE database](https://rest.db.ripe.net/) AS-SET objects. Uses X.509 certificate authentication via the RIPE REST API.

Built for [Poema-IX](https://ix.poema.eu.org/) and invoked by [IX-BIRD-RS-Generator](https://github.com/PoemaIX/IX-BIRD-RS-Generator) during its daily CI pipeline.

## How It Works

The library maintains an AS-SET object in the RIPE database to reflect the current membership of the IX. It fetches the existing AS-SET state, diffs it against the desired member list, and issues a PUT request to update RIPE if anything changed. A local JSON cache avoids unnecessary API calls when state is unchanged.

## Sync Scripts

Four entry-point scripts provide different strategies for determining the member list:

| Script | Input | Use Case |
|--------|-------|----------|
| `sync_from_config.py` | ARouteServer clients YAML | All configured members (regardless of session state) |
| `sync_from_estab.py` | Pre-generated establishment YAML | Members with established BGP sessions |
| `sync_from_bird.py` | Live BIRD `show protocols all` | Established sessions queried directly from BIRD |
| `sync_from_routes.py` | Live BIRD `show route` | Origin ASNs from active routes on a route server |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AS_SET` | Yes | Target AS-SET name (e.g. `AS-KSKB-IX`) |
| `RIPE_CLIENT_CERT` | Yes | X.509 client certificate (PEM) |
| `RIPE_CLIENT_KEY` | Yes | Private key (PEM) |
| `ARS_CLIENTS_PATH` | Script-dependent | Path to ARouteServer `clients.yml` |
| `CLIENTS_ASSET_PATH` | Script-dependent | Path to establishment YAML |
| `MAX_ASSET_LEN` | No | Maximum member count (default: 3000) |

## Library Usage

```python
from ripe_asset_sync import RipeAsSetClient

with RipeAsSetClient(
    as_set_name="AS-KSKB-IX",
    cert_pem=cert_pem_string,
    key_pem=key_pem_string,
    cache_dir="/tmp/cache",
) as client:
    current = client.get_current_members()
    client.sync_members(["AS-FOO", "AS-BAR", "AS65000"])
```

## Modules

- **`ripe_asset_sync.ripe_client`** — `RipeAsSetClient` for RIPE REST API interactions (fetch, diff, update)
- **`ripe_asset_sync.bird`** — Parsers for BIRD protocol/route output (`parse_bird_protocols`, `filter_established_sessions`, `parse_bird_routes_origin_asns`)
- **`ripe_asset_sync.arouteserver`** — Helpers to load and extract AS-SET data from ARouteServer client configs
- **`ripe_asset_sync.irr`** — `IrrCache` wrapping `bgpq4` queries with local expiry-based caching; includes `T1_ASNS` list

## Requirements

- Python >= 3.9
- `requests`, `pyyaml`
- `bgpq4` (system package, used by `IrrCache`)

## License

MIT
