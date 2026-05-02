import ipaddress
from subprocess import PIPE, Popen


def _getval(strin):
    return strin.split(":", 1)[1].strip()


def _getAddr(addr):
    addr = addr.strip()
    if "%" in addr:
        addr = addr.split("%", 1)
    else:
        addr = addr, None
    return ipaddress.ip_address(addr[0]), addr[1]


def _getAddrFromChannel(birdspaline):
    birdspaline = birdspaline.strip()
    if " " in birdspaline:
        addr, ll = birdspaline.split(" ", 1)
        if addr == "::":
            return ipaddress.ip_address(ll)
        return ipaddress.ip_address(addr)
    return ipaddress.ip_address(birdspaline)


def _getroutecount(birdspaline):
    birdspaline = birdspaline.strip()
    infos_list = list(map(lambda x: x.strip(), birdspaline.split(",")))
    infos = {"imported": None, "filtered": None, "exported": None, "preferred": None}
    for info in infos_list:
        val, key = info.strip().split(" ")
        val = int(val)
        infos[key] = val
    return infos


def parse_bird_protocols(birdc_output=None, n="*"):
    """Parse 'birdc show protocols all' output into structured session dicts.

    If birdc_output is None, runs birdc locally.
    """
    if birdc_output is None:
        if n == "*":
            n = '"*"'
        birdc_output = Popen(["birdc", "s", "p", "a", n], stdin=PIPE, stdout=PIPE).communicate()[0].decode()
    birdc_output = birdc_output.split("\n")[2:]
    birdc_output = "\n".join(birdc_output).split("\n\n")
    result_list = []
    for proto_str in birdc_output:
        proto_str_line = proto_str.split("\n")
        protoinfo = proto_str_line[0].strip().split()
        if len(protoinfo) < 3:
            continue
        proto_name, proto_type = protoinfo[0], protoinfo[1]
        if proto_type != "BGP":
            continue
        result = {
            "name": proto_name,
            "state": None,
            "as": {"local": 0, "remote": 0},
            "addr": {"af": 0, "local": None, "remote": None, "interface": None},
            "route": {
                "ipv4": {"imported": 0, "exported": 0, "preferred": 0},
                "ipv6": {"imported": 0, "exported": 0, "preferred": 0},
            },
        }
        current_channel = ""
        for L in proto_str_line:
            if "BGP state:" in L:
                result["state"] = _getval(L)
            elif "Neighbor AS:" in L:
                result["as"]["remote"] = int(_getval(L))
            elif "Local AS" in L:
                result["as"]["local"] = int(_getval(L))
            elif "Neighbor address:" in L:
                remote = _getval(L)
                addrobj, interface = _getAddr(remote)
                result["addr"]["interface"] = interface
                result["addr"]["remote"] = str(addrobj)
                if type(addrobj) == ipaddress.IPv4Address:
                    result["addr"]["af"] = 4
                elif type(addrobj) == ipaddress.IPv6Address:
                    result["addr"]["af"] = 6
            elif "Channel" in L:
                current_channel = L.split("Channel ")[1].strip()
            elif "Routes:" in L:
                result["route"][current_channel] = _getroutecount(_getval(L))
            elif "BGP Next hop:" in L:
                if (result["addr"]["af"] == 4 and current_channel == "ipv4") or (
                    result["addr"]["af"] == 6 and current_channel == "ipv6"
                ):
                    result["addr"]["local"] = str(_getAddrFromChannel(_getval(L)))
        result_list.append(result)
    return result_list


def filter_established_sessions(sessions, min_imported=1, address_family="ipv6"):
    """Return set of remote ASNs from Established sessions with >= min_imported routes."""
    return set(
        s["as"]["remote"]
        for s in sessions
        if s["state"] == "Established" and s["route"][address_family].get("imported", 0) >= min_imported
    )


def session_to_dict(sessions):
    """Group session list by remote ASN."""
    result = {}
    for sess in sessions:
        key = sess["as"]["remote"]
        if key in result:
            result[key].append(sess)
        else:
            result[key] = [sess]
    return result


def parse_bird_routes_origin_asns(route_output):
    """Parse 'birdc show route ... all' output, extract origin ASNs from as_path."""
    asns = {}
    for line in route_output.split("\n"):
        if "as_path" in line:
            bgp_last = line.split(" ")[-1]
            if bgp_last.isnumeric():
                asns[int(bgp_last)] = 0
    return sorted(asns.keys())
