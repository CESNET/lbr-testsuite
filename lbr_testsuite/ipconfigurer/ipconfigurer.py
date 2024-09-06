"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
        Jan Kucera <jan.kucera@cesnet.cz>
        Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2020 CESNET, z.s.p.o.

API for ip configuration using pyroute2 library.
"""

import errno
import socket
import time

from pr2modules import netns
from pr2modules.iproute import IPRoute
from pr2modules.netlink.exceptions import NetlinkError
from pr2modules.netlink.rtnl.ifinfmsg import IFF_ALLMULTI, IFF_PROMISC
from pr2modules.nslink.nslink import NetNS


IFA_F_SECONDARY = 0x01
# IFA_F_TEMPORARY IFA_F_SECONDARY
IFA_F_NODAD = 0x02
IFA_F_OPTIMISTIC = 0x04
IFA_F_DADFAILED = 0x08
IFA_F_HOMEADDRESS = 0x10
IFA_F_DEPRECATED = 0x20
IFA_F_TENTATIVE = 0x40
IFA_F_PERMANENT = 0x80
IFA_F_MANAGETEMPADDR = 0x100
IFA_F_NOPREFIXROUTE = 0x200
IFA_F_MCAUTOJOIN = 0x400
IFA_F_STABLE_PRIVACY = 0x800


class IpConfigurerError(NetlinkError):
    """An error of our API implementation on top of pyroute2
    library so we do not have to directly raise NetlinkError and
    also can easily catch such exceptions and distinguish them
    from other unexpected errors.
    """

    pass


def _get_ipr_context(namespace=None):
    if namespace:
        return NetNS(namespace)

    return IPRoute()


def _extract_attr_tuples(obj):
    """Extract all attributes of pyroute object which are present in a form
    of a named list of (key, values) tuples. It discards the name of the list
    and enables access to the property value using the key of the original tuple.

    Parameters
    ----------
    obj : dict()
        Pyroute object, returned by e.g. get_links()[0] or get_routes()[0]

    Returns
    -------
    dict()
        Dictionary of pyroute object attributes with extracted tuple items.
    """

    attrs = {}
    for key, val in obj.items():
        if isinstance(val, list):
            for tup in val:
                attrs[tup[0]] = tup[1]
            continue

        attrs[key] = val

    return attrs


def _link_lookup_first(ifc_name, namespace=None):
    with _get_ipr_context(namespace) as ipr:
        links = ipr.link_lookup(ifname=ifc_name)
    if not links:
        raise IpConfigurerError(
            errno.ENODEV,
            f"No such interface '{ifc_name}' in namespace '{namespace}'.",
        )
    return links[0]


##
# Addresses
##
def _manipulate_ip_addr(
    cmd,
    ifc_name,
    address,
    prefixlen,
    family=socket.AF_INET,
    ifa_flags=None,
    namespace=None,
):
    assert cmd == "add" or cmd == "del"

    with _get_ipr_context(namespace) as ipr:
        ifc_index = _link_lookup_first(ifc_name, namespace)
        params = dict(
            index=ifc_index,
            address=address,
            prefixlen=prefixlen,
            family=family,
        )
        if ifa_flags:
            params["IFA_FLAGS"] = ifa_flags
        ipr.addr(cmd, **params)


def add_ip_addr(
    ifc_name,
    address,
    prefixlen,
    family=socket.AF_INET,
    ifa_flags=None,
    namespace=None,
    safe=False,
):
    """Add an IP address to the interface.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    ifc_name : str
        Name of an interface to which the IP address should be added.
    address : str
        IP address to add.
    prefixlen : int
        IP address network prefix length.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    ifa_flags : int, optional
        Specific flags for added IP address.
    namespace : str, optional
        Name of a namespace.
    safe: bool, optional
        Ignore an error if the address is already present.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_ip_addr("add", ifc_name, address, prefixlen, family, ifa_flags, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.EEXIST:
            raise err
        return False
    return True


def delete_ip_addr(
    ifc_name,
    address,
    prefixlen,
    family=socket.AF_INET,
    namespace=None,
    safe=False,
):
    """Delete an IP address from the interface

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    ifc_name : str
        Name of an interface to which the IP address should be added.
    address : str
        IP address to add.
    prefixlen : int
        IP address network prefix length.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    namespace : str, optional
        Name of a namespace.
    safe: bool, optional
        Ignore an error if the address or target interface do not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_ip_addr("del", ifc_name, address, prefixlen, family, None, namespace)
    except NetlinkError as err:
        if not safe or (err.code != errno.EADDRNOTAVAIL and err.code != errno.ENODEV):
            raise err
        return False
    return True


##
# Interfaces
##
def ifc_set_mac(ifc_name, mac_addr, namespace=None):
    """Set a new mac address of an interface.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    mac_addr : str
        New mac address.
    namespace : str, optional
        Name of a namespace.
    """

    with _get_ipr_context(namespace) as ipr:
        ipr.link("set", ifname=ifc_name, address=mac_addr)


def _ifc_up_down(state, ifc_name, namespace=None):
    assert state == "up" or state == "down"

    with _get_ipr_context(namespace) as ipr:
        ipr.link("set", ifname=ifc_name, state=state)


def ifc_up(ifc_name, namespace=None):
    """Turn an interface up.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    namespace : str, optional
        Name of a namespace.
    """

    _ifc_up_down("up", ifc_name, namespace)


def ifc_down(ifc_name, namespace=None, safe=False):
    """Turn an interface down.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if the target interface does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _ifc_up_down("down", ifc_name, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.ENODEV:
            raise err
        return False
    return True


def ifc_status(ifc_name, namespace=None):
    """Get interface status.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    namespace : str, optional
        Name of a namespace.

    Raises
    ------
    IpConfigurerError
        When interface does not exist.

    Returns
    -------
    dict()
        Dictionary of interface status attributes.
    """

    with _get_ipr_context(namespace) as ipr:
        links = ipr.get_links(ifname=ifc_name)

    if not links:
        raise IpConfigurerError(
            errno.ENODEV,
            f"No such interface '{ifc_name}' in namespace '{namespace}'.",
        )

    return _extract_attr_tuples(links[0])


def ifc_set_master(
    ifc_name,
    master=None,
    namespace=None,
):
    """Set a master for the interface. If the master parameter is None,
    the master interface is removed.

    Effectively, it is equivalent of using the following commands::

        ip link set [slave-ifc] master [master-ifc]
        ip link set [slave-ifc] nomaster

    Parameters
    ----------
    name : str
        Name of the interface.
    master : str, optional
        Master interface name to be set.
    namespace : str, optional
        Name of the namespace to operate in.
    """

    with _get_ipr_context(namespace) as ipr:
        links = ipr.link_lookup(ifname=ifc_name)
        if not links:
            raise RuntimeError(f"No such interface '{ifc_name}' in namespace '{namespace}'.")
        index = links[0]

        master_index = 0
        if master is not None:
            links = ipr.link_lookup(ifname=master)
            if not links:
                raise RuntimeError(f"No such interface '{master}' in namespace '{namespace}'.")
            master_index = links[0]

        ipr.link("set", index=index, master=master_index)


def ifc_get_master_name(
    slave_name,
    namespace=None,
):
    """Get the name of master interface of the specified slave interface.

    Parameters
    ----------
    slave_name : str
        Name of the slave interface.
    namespace : str, optional
        Name of the namespace to operate in.

    Returns
    -------
    str or None
        Name of the master interface.
        None if interface does not have a master.
    """

    with _get_ipr_context(namespace) as ipr:
        links = ipr.get_links(ifname=slave_name)

        if not links:
            raise RuntimeError(f"No such interface '{slave_name}' in namespace '{namespace}'.")

        ifc = links[0]
        index = ifc.get_attr("IFLA_MASTER")
        if not index:
            return None

        master_links = ipr.get_links(index=index)

    if not master_links:
        raise RuntimeError(f"Interface with index {index} does not exist")

    master = master_links[0]
    return master.get_attr("IFLA_IFNAME")


def ifc_carrier(ifc_name, namespace=None):
    """Get interface carrier.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    namespace : str, optional
        Name of a namespace.

    Returns
    -------
    int
        Interface carrier.
    """

    status = ifc_status(ifc_name, namespace)
    return status["IFLA_CARRIER"]


def wait_until_ifc_carrier(ifc_name, namespace=None, timeout=1):
    """Wait until an interface has carrier. The interface is specified by its name.

    If the interface does not have carrier in a specified time an exception is raised.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    namespace : str, optional
        Name of a namespace.
    timeout : int, optional
        Maximal time (seconds) to wait for carrier.

    Raises
    ------
    IpConfigurerError
        If the the link is not up after the timeout.
    """

    now = started = time.monotonic()

    while True:
        if ifc_carrier(ifc_name, namespace):
            return

        if now - started > timeout:
            raise IpConfigurerError(
                errno.ETIME,
                f"No carrier on interface '{ifc_name}' (waited {timeout} seconds).",
            )

        time.sleep(1)
        now = time.monotonic()


def ifc_set_allmulticast(ifc_name, state, namespace=None):
    """Set the allmulticast flag of an interface.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    state : bool
        Enable or disable flag.
    namespace : str, optional
        Name of a namespace.
    """

    with _get_ipr_context(namespace) as ipr:
        links = ipr.get_links(ifname=ifc_name)
        flags = links[0]["flags"]

        if state:
            flags |= IFF_ALLMULTI
        else:
            flags &= ~IFF_ALLMULTI

        ipr.link("set", ifname=ifc_name, flags=flags)


def ifc_set_promisc(ifc_name, state, namespace=None):
    """Set the promiscuous flag of an interface.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    state : bool
        Enable or disable flag.
    namespace : str, optional
        Name of a namespace.
    """

    with _get_ipr_context(namespace) as ipr:
        links = ipr.get_links(ifname=ifc_name)
        flags = links[0]["flags"]

        if state:
            flags |= IFF_PROMISC
        else:
            flags &= ~IFF_PROMISC

        ipr.link("set", ifname=ifc_name, flags=flags)


def ifc_set_mtu(ifc_name, mtu, namespace=None):
    """Set the mtu of an interface.

    Parameters
    ----------
    ifc_name : str
        Name of an interface.
    mtu : int
        Size of MTU.
    namespace : str, optional
        Name of a namespace.
    """

    with _get_ipr_context(namespace) as ipr:
        ipr.link("set", ifname=ifc_name, mtu=mtu)


##
# Routes
##
def _manipulate_route(
    cmd,
    destination,
    gateway,
    table,
    family=socket.AF_INET,
    prefsrc=None,
    namespace=None,
):
    assert cmd == "add" or cmd == "del"

    with _get_ipr_context(namespace) as ipr:
        params = dict(
            dst=destination,
            gateway=gateway,
        )
        if table:
            params["table"] = table
        if prefsrc:
            params["prefsrc"] = prefsrc

        ipr.route(cmd, **params)


def add_route(
    destination,
    gateway,
    table=None,
    family=socket.AF_INET,
    prefsrc=None,
    namespace=None,
    safe=False,
):
    """Add a route.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    destination : str
        Destination network in format <IP address>/<mask>
    gateway : str
        IP address of gateway (next hop).
    table : int, optional
        Routing table ID.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    prefsrc : str, optional
        Prefered source IP address.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if the route already exists.


    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_route("add", destination, gateway, table, family, prefsrc, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.EEXIST:
            raise err
        return False
    return True


def delete_route(
    destination,
    gateway,
    table=None,
    family=socket.AF_INET,
    prefsrc=None,
    namespace=None,
    safe=False,
):
    """Delete a route.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    A route is delete only if exists. Nonexisting route is not
    considered as error as due to routing table optimalization
    a removal of adjacent route could remove more specific one.

    Parameters
    ----------
    destination : str
        Destination network in format <IP address>/<mask>
    gateway : str
        IP address of gateway (next hop).
    table : int, optional
        Routing table ID.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    prefsrc : str, optional
        Prefered source IP address.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if the route does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_route("del", destination, gateway, table, family, prefsrc, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.ESRCH:
            raise err
        return False
    return True


##
# Namespaces
##
def create_namespace(namespace):
    """Create a namespace.

    Parameters
    ----------
    namespace : str
        Name of a namespace.
    """

    nns = NetNS(namespace)
    nns.close()


def delete_namespace(namespace, safe=False):
    """Delete a namespace.

    Parameters
    ----------
    namespace : str
        Name of a namespace.
    safe : bool, optional
        Ignore an error if the route does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        netns.remove(namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.ENODEV:
            raise err
        return False
    return True


##
# Links
##
def add_link(
    name,
    kind,
    link=None,
    address=None,
    macvlan_mode=None,
    namespace=None,
    master_link_namespace=None,
    vlan_id=None,
    peer=None,
    safe=False,
):
    """Add a link.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    name : str
        Name of a link.
    kind : str
        Link kind.
    link : str, optional
        Master interface for specific link types (e.g. VLAN).
    address : str, optional
        MAC address.
    macvlan_mode : str, optional
        Mode for macvlan link kind.
    namespace : str, optional
        Name of a namespace where the link should be added.
    master_link_namespace : str, optional
        Name of namespace where the master link (the link argument) is located.
    vlad_id : int, optional
        VLAN ID for VLAN link kind.
    peer : str, optional
        Peer interface name for veth link kind.
    safe : bool, optional
        Ignore an error if the link already exists.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    with _get_ipr_context(master_link_namespace) as ipr:
        params = dict(
            ifname=name,
            kind=kind,
        )
        if link:
            if master_link_namespace:
                ifc_index = _link_lookup_first(link, namespace)
            else:
                ifc_index = _link_lookup_first(link, master_link_namespace)
            params["link"] = ifc_index
        if address:
            params["address"] = address
        if macvlan_mode:
            params["macvlan_mode"] = macvlan_mode
        if namespace:
            params["net_ns_fd"] = namespace
        if vlan_id:
            params["vlan_id"] = vlan_id
        if peer:
            params["peer"] = peer

        try:
            ipr.link("add", **params)
        except NetlinkError as err:
            if not safe or err.code != errno.EEXIST:
                raise err
            return False
        return True


def delete_link(
    name,
    kind=None,
    link=None,
    namespace=None,
    vlan_id=None,
    safe=False,
):
    """Add a link.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    name : str
        Name of a link.
    kind : str
        Link kind.
    link : str, optional
        Master interface or specific link types (e.g. VLAN).
    namespace : str, optional
        Name of a namespace.
    vlad_id : int, optional
        VLAN ID for VLAN link kind.
    safe : bool, optional
        Ignore an error if the link does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    with _get_ipr_context(namespace) as ipr:
        params = dict(ifname=name)
        if kind:
            params["kind"] = kind
        if link:
            try:
                params["link"] = _link_lookup_first(link, namespace)
            except NetlinkError as err:
                if not safe or err.code != errno.ENODEV:
                    raise err
                return False
        if vlan_id:
            params["vlan_id"] = vlan_id

        try:
            ipr.link("del", **params)
        except NetlinkError as err:
            if not safe or err.code != errno.ENODEV:
                raise err
            return False
        return True


def link_exists(name, namespace=None):
    """Check whether a link exists.

    Parameters
    ----------
    name : str
        Name of a link.
    namespace : str, optional
        Name of a namespace.

    Returns
    -------
    bool
        True if link exists, False otherwise.
    """

    link = None
    with _get_ipr_context(namespace) as ipr:
        link = ipr.link_lookup(ifname=name)

    return len(link) > 0


##
# Neighbours
##
def _manipulate_ip_neigh(
    cmd,
    ifc_name,
    address,
    lladdr,
    family=socket.AF_INET,
    state="permanent",
    namespace=None,
):
    assert cmd == "add" or cmd == "del" or cmd == "change"

    with _get_ipr_context(namespace) as ipr:
        ifc_index = _link_lookup_first(ifc_name, namespace)
        params = dict(
            ifindex=ifc_index,
            dst=address,
            lladdr=lladdr,
            family=family,
            state=state,
        )

        ipr.neigh(cmd, **params)


def add_ip_neigh(
    ifc_name,
    address,
    lladdr,
    family=socket.AF_INET,
    state="permanent",
    namespace=None,
    safe=False,
):
    """Add an IP neighbour (ARP/NDP cache entry).

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    ifc_name : str
        Name of an interface connected to the neighbour.
    address : str
        IP address of neighbour.
    lladdr : str
        MAC address of neighbour.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    state : str, optional
        Neighbour cache entry state.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if neighbour already exists.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_ip_neigh("add", ifc_name, address, lladdr, family, state, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.EEXIST:
            raise err
        return False
    return True


def change_ip_neigh(
    ifc_name,
    address,
    lladdr,
    family=socket.AF_INET,
    state="permanent",
    namespace=None,
    safe=False,
):
    """Change an existing IP neighbour (ARP/NDP cache entry). If the
    record does not exist, fail.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    ifc_name : str
        Name of an interface connected to the neighbour.
    address : str
        IP address of neighbour.
    lladdr : str
        MAC address of neighbour.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    state : str, optional
        Neighbour cache entry state.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if neighbour does not exists.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_ip_neigh("change", ifc_name, address, lladdr, family, state, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.ENOENT:
            raise err
        return False
    return True


def delete_ip_neigh(
    ifc_name,
    address,
    lladdr,
    family=socket.AF_INET,
    state="permanent",
    namespace=None,
    safe=False,
):
    """Delete an IP neighbour (ARP/NDP cache entry).

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    ifc_name : str
        Name of an interface connected to the neighbour.
    address : str
        IP address of neighbour.
    lladdr : str
        MAC address of neighbour.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    state : str, optional
        Neighbour cache entry state.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if neighbour does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    try:
        _manipulate_ip_neigh("del", ifc_name, address, lladdr, family, state, namespace)
    except NetlinkError as err:
        if not safe or err.code != errno.ENOENT:
            raise err
        return False
    return True


##
# VLANs
##
def add_vlan(name, link, vlan_id, namespace=None, master_link_namespace=None, safe=False):
    """Add a VLAN.

    Add a new link for a VLAN, set IP address and bring the link up.

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    name : str
        Name of a link.
    link : str
        Master interface name.
    vlad_id : int
        VLAN ID.
    namespace : str, optional
        Name of a namespace where the link should be added.
    master_link_namespace : str, optional
        Name of namespace where the master link (the link argument) is located.
    safe : bool, optional
        Ignore an error if the link already exists.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    return add_link(
        name,
        "vlan",
        link,
        vlan_id=vlan_id,
        namespace=namespace,
        master_link_namespace=master_link_namespace,
        safe=safe,
    )


def delete_vlan(name, link, vlan_id, namespace=None, safe=False):
    """Delete a VLAN link

    Most of the arguments corresponds to the appropriate method from
    pyroute2 library.

    Parameters
    ----------
    name : str
        Name of a link.
    link : str
        Master interface name.
    vlad_id : int
        VLAN ID.
    namespace : str, optional
        Name of a namespace.
    safe : bool, optional
        Ignore an error if the vlan does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    return delete_link(name, "vlan", link, vlan_id=vlan_id, namespace=namespace, safe=safe)


##
# Rules
##
def _rule_match_attr(rule, key, value):
    for att in rule["attrs"]:
        if att[0] == key:
            return att[1] == value

    return False


def _rule_contains_attr(rule, key):
    for att in rule["attrs"]:
        if att[0] == key:
            return True

    return False


def _rule_match(rule, table, iif=None, oif=None, fwmark=None, priority=None):
    if rule["table"] != table:
        return False

    if priority is not None:
        atts = _extract_attr_tuples(rule)
        if "FRA_PRIORITY" in atts and atts["FRA_PRIORITY"] != priority:
            return False

    if fwmark is not None:
        if not _rule_match_attr(rule, "fwmark", fwmark):
            return False

    if iif is not None and oif is not None:
        return _rule_match_attr(rule, "FRA_IIFNAME", iif) and _rule_match_attr(
            rule, "FRA_OIFNAME", oif
        )

    elif iif is not None:
        return _rule_match_attr(rule, "FRA_IIFNAME", iif) and not _rule_contains_attr(
            rule, "FRA_OIFNAME"
        )

    elif oif is not None:
        return _rule_match_attr(rule, "FRA_OIFNAME", oif) and not _rule_contains_attr(
            rule, "FRA_IIFNAME"
        )

    else:
        return not _rule_contains_attr(rule, "FRA_IIFNAME") and not _rule_contains_attr(
            rule, "FRA_OIFNAME"
        )


def _manipulate_rule(
    cmd,
    table,
    iif=None,
    oif=None,
    fwmark=None,
    family=socket.AF_INET,
    priority=None,
):
    assert cmd == "add" or cmd == "del"

    kwargs = {
        "table": table,
        "family": family,
    }

    if iif is not None:
        kwargs["FRA_IIFNAME"] = iif
    if oif is not None:
        kwargs["FRA_OIFNAME"] = oif
    if fwmark is not None:
        kwargs["fwmark"] = fwmark

    if priority is not None:
        kwargs["priority"] = priority

    with _get_ipr_context() as ipr:
        ipr.rule(cmd, **kwargs)


def _format_rule_match_errmsg(kwargs):
    msg = ""

    if "iif" in kwargs:
        iif = kwargs["iif"]
        msg += f" and iif {iif}"

    if "oif" in kwargs:
        oif = kwargs["oif"]
        msg += f" and oif {oif}"

    if "fwmark" in kwargs:
        fwm = kwargs["fwmark"]
        msg += f" and fwmark {fwm}"

    return msg


def add_rule(
    table,
    iif_name=None,
    oif_name=None,
    fwmark=None,
    family=socket.AF_INET,
    priority=None,
    safe=False,
):
    """Add a rule.

    Parameters
    ----------
    table : int
        Routing table ID.
    iif_name : str, optional
        Name of a related iif interface.
    oif_name : str, optional
        Name of a related oif interface.
    fwmark : int, optional
        Firewall mark group number.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    priority : int, optional
        Priority of route.
    safe : bool, optional
        Skip the addition if the rule already exists to not duplicate it.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    kwargs = {
        "priority": priority,
    }
    if iif_name is not None:
        kwargs["iif"] = iif_name
    if oif_name is not None:
        kwargs["oif"] = oif_name
    if fwmark is not None:
        kwargs["fwmark"] = fwmark

    with _get_ipr_context() as ipr:
        curr_rules = ipr.get_rules(
            family=family,
            match=lambda x: _rule_match(x, table, **kwargs),
        )

    if curr_rules:
        if safe:
            return False
        raise IpConfigurerError(
            errno.EEXIST,
            f"The rule already exists for table '{table}' {_format_rule_match_errmsg(**kwargs)}.",
        )

    kwargs["family"] = family

    _manipulate_rule("add", table, **kwargs)
    return True


def delete_rule(
    table,
    iif_name=None,
    oif_name=None,
    fwmark=None,
    family=socket.AF_INET,
    priority=None,
    safe=False,
):
    """Delete a rule.

    Parameters
    ----------
    table : int
        Routing table ID.
    iif_name : str, optional
        Name of a related iif interface.
    oif_name : str, optional
        Name of a related oif interface.
    fwmark : int, optional
        Firewall mark group number.
    family : socket.AF_INET | socket.AF_INET6, optional
        IP address family - socket.AF_INET for IPv4, socket.AF_INET6
        for IPv6.
    priority : int, optional
        Priority of route.
    safe : bool, optional
        Ignore an error if the rule does not exist.

    Returns
    -------
    bool
        True on success, False otherwise
    """

    kwargs = {
        "family": family,
        "priority": priority,
    }
    if iif_name is not None:
        kwargs["iif"] = iif_name
    if oif_name is not None:
        kwargs["oif"] = oif_name
    if fwmark is not None:
        kwargs["fwmark"] = fwmark

    try:
        _manipulate_rule("del", table, **kwargs)
    except NetlinkError as err:
        if not safe or err.code != errno.ENOENT:
            raise err
        return False
    return True
