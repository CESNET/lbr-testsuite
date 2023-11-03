"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Module implements interface of IP addresses format for traffic generators.
"""

import ipaddress

from . import random_types


class BaseIPAddresses:
    """Base class for common interface of IP addresses format.

    This class cannot be used directly. Certain parts need to be implemented
    in derived classes for IPv4 and IPv6 addresses.

    Parameters
    ----------
    addresses : str or list or dict or ``random_types.RandomIP``
        IP addresses. Detailed description is in derived classes.
    restrict_prefix_length : bool (optional)
        By default, class won't allow prefixes containing more
        than 2^16 addresses. The reason is that expansion (converting
        prefix to list of individual adressess) would require
        computational and memory resources. This check can be
        turned off, but user then takes responsibility.
    """

    _SINGLE_IP = "single-ip"
    _SINGLE_PREFIX = "single-prefix"
    _IP_LIST = "ip-list"

    _SUPPORTED_NON_LIST_TYPES = (str,)

    _VERSION = None
    _PREFIX_MAXLEN = None
    _RESTRICTED_PREFIX_LEN = 16

    def __init__(self, addresses, restrict_prefix_length=True):
        assert self._VERSION is not None, "Class parameter _VERSION must be defined"
        assert self._PREFIX_MAXLEN is not None, "Class parameter _PREFIX_MAXLEN must be defined"

        self._random_flag = False
        self._restricted = restrict_prefix_length
        self._addr_list = None

        # Convert dict/RandomIP to list of addresses
        if isinstance(addresses, dict):
            addresses = self._dict_to_list(addresses)
        elif isinstance(addresses, random_types.RandomIP):
            self._random_flag = True
            addresses = addresses.generate(version=self._VERSION)
            if len(addresses) == 1:
                addresses = addresses[0]

        if isinstance(addresses, self._SUPPORTED_NON_LIST_TYPES):
            self._addr_list = [addresses]

            if ipaddress.ip_network(addresses).num_addresses == 1:
                self._type = self._SINGLE_IP
            else:
                self._type = self._SINGLE_PREFIX

        elif isinstance(addresses, list):
            self._type = self._IP_LIST
            flat_list = []

            # Replace dicts/RandomIP with lists
            for i, net in enumerate(addresses):
                if isinstance(net, dict):
                    addresses[i] = self._dict_to_list(net)
                if isinstance(net, random_types.RandomIP):
                    self._random_flag = True
                    addresses[i] = net.generate(version=self._VERSION)

            # Flatten list (eg. from [1, [2, 3], 4] to [1, 2, 3, 4])
            # Needed only if dicts/RandomIP were converted to lists
            for item in addresses:
                if isinstance(item, list):
                    flat_list.extend(item)
                else:
                    flat_list.append(item)

            self._addr_list = flat_list

        else:
            assert False, (
                f"Input must be one of following types: "
                f"{self._SUPPORTED_NON_LIST_TYPES + tuple([dict, list, random_types.RandomIP])}"
            )

        for net in self._addr_list:
            assert (
                ipaddress.ip_network(net).version == self._VERSION
            ), f"Only IPv{self._VERSION} addresses are supported"

    def is_single_ip(self):
        """Return True if input was a single IP address."""

        return self._type == self._SINGLE_IP

    def is_single_prefix(self):
        """Return True if input was a single IP prefix."""

        return self._type == self._SINGLE_PREFIX

    def is_ip_list(self):
        """Return True if input was a list (dict and
        random type gets converted to list)."""

        return self._type == self._IP_LIST

    def is_random(self):
        """Return True if any address is random.

        This flag is also enabled if list contains any
        ``random_types.RandomIP`` item.

        Returns
        ------
        bool
            True if addresses are random, False otherwise.
        """

        return self._random_flag

    def addresses_count(self):
        """Return number of all IP addresses (all prefixes/dicts/list are expanded).

        For example, if addresses were set as ['10.0.0.0/28',
        '15.0.0.0', {'first': '20.0.0.0', 'count': 4}], then output will
        contain 16 + 1 + 4 = 21 addresses (includes network and
        broadcast addresses). It is equivalent to
        ``len(addresses_as_list())``, except it's faster and more
        effective.

        Returns
        ------
        int
            Number of IP Addresses.
        """

        addrs = 0
        for net in self._addr_list:
            addrs += ipaddress.ip_network(net).num_addresses

        return addrs

    def hosts_count(self):
        """Return number of all hosts (all prefixes/dicts/list are expanded).

        For example, if addresses were set as ['10.0.0.0/28',
        '15.0.0.0', {'first': '20.0.0.0', 'count': 4}], then output will
        contain 14 + 1 + 4 = 19 addresses.

        If addresses were set as 'aaaa::/124', then output will contain 15 addresses.

        See ``addresses_count`` and ``hosts_as_list`` for details.

        Returns
        ------
        int
            Number of IP Addresses.
        """

        addrs = 0
        for net in self._addr_list:
            network = ipaddress.ip_network(net)
            addrs += network.num_addresses
            if network.version == 4 and network.prefixlen <= 30:
                addrs -= 2
            # In IPv6 broadcast is replaced by multicast - as such
            # broadcast address is considered usable host
            elif network.version == 6 and network.prefixlen <= 126:
                addrs -= 1

        return addrs

    def _dict_to_list(self, addrs):
        """Convert dict format to list of IP addresses

        Dict has following format:
            {first='10.0.0.0', count=150, step=2}

        Keys 'first' and 'count' are required.
        Key 'step' is optional. Default value is 1.
        """

        assert "first" in addrs, 'Dict must have following key: "first"'
        assert "count" in addrs, 'Dict must have following key: "count"'
        assert isinstance(
            addrs["first"], self._SUPPORTED_NON_LIST_TYPES
        ), f'Key "first" must be one of following types: {self._SUPPORTED_NON_LIST_TYPES}'

        step = addrs["step"] if "step" in addrs else 1
        if self._restricted:
            assert addrs["count"] <= 2**self._RESTRICTED_PREFIX_LEN, (
                f"Class does not allow more than {addrs['count']} addresses "
                "for dict type in restricted mode."
            )

        first_ip = ipaddress.ip_address(addrs["first"])
        conv_addrs = [first_ip]
        for i in range(1, addrs["count"]):
            conv_addrs.append(first_ip + i * step)

        return conv_addrs

    def _addrs_from_net(self, network):
        """Return list of addresses in network (including
        network and broadcast address)."""

        addresses = set(network.hosts())
        addresses.add(network.network_address)
        addresses.add(network.broadcast_address)

        return list(addresses)

    def addresses_as_list(self):
        """Return addresses in form of list.

        Returns
        ------
        list(str)
            IP addresses.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        addresses = []

        if self._restricted:
            assert len(self._addr_list) <= 2**self._RESTRICTED_PREFIX_LEN, (
                f"Class does not allow more than {2**self._RESTRICTED_PREFIX_LEN} "
                f"addresses in list when in restricted mode."
            )

        for net in self._addr_list:
            network = ipaddress.ip_network(net)
            if self._restricted:
                assert network.num_addresses <= 2**self._RESTRICTED_PREFIX_LEN, (
                    "Class does not allow prefix lengths to be less "
                    f"than {self._PREFIX_MAXLEN - self._RESTRICTED_PREFIX_LEN} in restricted mode."
                )
            addresses.extend(self._addrs_from_net(network))

        return list(map(str, addresses))

    def hosts_as_list(self):
        """Return usable hosts in form of list.

        Returns
        ------
        list(str)
            Hosts.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        hosts = []

        if self._restricted:
            assert len(self._addr_list) <= 2**self._RESTRICTED_PREFIX_LEN, (
                f"Class does not allow more than {2**self._RESTRICTED_PREFIX_LEN} "
                f"addresses in list when in restricted mode."
            )

        for net in self._addr_list:
            network = ipaddress.ip_network(net)
            if self._restricted:
                assert network.num_addresses <= 2**self._RESTRICTED_PREFIX_LEN, (
                    "Class does not allow prefix lengths to be less "
                    f"than {self._PREFIX_MAXLEN - self._RESTRICTED_PREFIX_LEN} in restricted mode."
                )
            hosts.extend(list(network.hosts()))

        return list(map(str, hosts))

    def first_ip(self):
        """Return first IP address.

        It is the first address in the list or the
        first address in the IP prefix (i.e. network address).

        Returns
        -------
        str
            IP address.
        """

        return str(ipaddress.ip_network(self._addr_list[0]).network_address)

    def last_ip(self):
        """Return last IP address.

        It is the last address in the list or the
        last address in the IP prefix (i.e. broadcast address).

        Returns
        -------
        str
            IP address.
        """

        return str(ipaddress.ip_network(self._addr_list[-1]).broadcast_address)


class IPv4Addresses(BaseIPAddresses):
    """Common interface for IPv4 addresses format.

    This class defines format of IPv4 addresses when using high-level
    API for packet creation in traffic generators.

    Parameters
    ----------
    addresses : str or list or dict or ``random_types.RandomIP`` or
                ipaddress.IPv4Address or ipaddress.IPv4Network
        Can be set as:
            - single address (``10.0.0.0``)
            - prefix (``10.0.0.0/24``)
            - dict (``{first='10.0.0.0', count=150, step=1}``)
            - random (``random_types.RandomIP``)
            - types from ``ipaddress`` module
            - list of previous formats (``['11.0.0.0/24', {first='12.0.0.0', count=100}]``)

        For dict format the key ``step`` is optional (default value is 1).
    restrict_prefix_length : bool (optional)
        By default, class won't allow prefixes with prefix length
        below 16. This limits number of addresses to 2^16 or 65536.
        The reason is that expansion (converting prefix to list of
        individual adressess) would require computational and memory
        resources. This check can be turned off, but user then takes
        responsibility.
    """

    _SUPPORTED_NON_LIST_TYPES = (
        str,
        ipaddress.IPv4Address,
        ipaddress.IPv4Network,
    )
    _VERSION = 4
    _PREFIX_MAXLEN = 32

    def addresses_as_list(self):
        """Return addresses in form of sorted list.

        Returns
        ------
        list(ipaddress.IPv4Address)
            IP addresses.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        addresses = super().addresses_as_list()
        addresses = list(map(ipaddress.ip_address, addresses))
        addresses.sort()
        return addresses

    def hosts_as_list(self):
        """Return usable hosts in form of sorted list.

        This method differs from ``addresses_as_list`` as it does
        **not** include network and broadcast address when prefix
        length (PF) is 30 or lower. For PF 31, both network and broadcast
        address are returned. For PF 32, empty list is returned.

        Returns
        ------
        list(ipaddress.IPv4Address)
            Hosts.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        hosts = super().hosts_as_list()
        hosts = list(map(ipaddress.ip_address, hosts))
        hosts.sort()
        return hosts

    def address_generator(self):
        """Return address generator.

        You can use this as::

            for ipaddr in address_generator():
                print(ipaddr)

        Returns
        ------
        generator(ipaddress.IPv4Address)
            IP addresses generator.
        """

        for net in self._addr_list:
            network = ipaddress.ip_network(net)

            if network.prefixlen <= 30:
                yield network.network_address
                for addr in network.hosts():
                    yield addr
                yield network.broadcast_address
            elif network.prefixlen == 31:
                yield network.network_address
                yield network.broadcast_address
            else:
                yield network.network_address

    def host_generator(self):
        """Return host generator.

        You can use this as::

            for host in host_generator():
                print(host)

        Returns
        ------
        generator(ipaddress.IPv4Address)
            IP host generator.
        """

        for net in self._addr_list:
            network = ipaddress.ip_network(net)

            if network.prefixlen <= 31:
                for addr in network.hosts():
                    yield addr
            else:
                yield network.network_address


class IPv6Addresses(BaseIPAddresses):
    """Common interface for IPv6 addresses format.

    This class defines format of IPv6 addresses when using high-level
    API for packet creation in traffic generators.

    Parameters
    ----------
    addresses : str or list or dict or ``random_types.RandomIP`` or
                ipaddress.IPv6Address or ipaddress.IPv6Network
        Can be set as:
            - single address (``2001:db8::1``)
            - prefix (``2001:db8::/48``)
            - dict (``{first='2001:db8::', count=150, step=1}``)
            - random (``random_types.RandomIP``)
            - types from ``ipaddress`` module
            - list of previous formats (``['2001:db8::/48', {first='2001:db8::', count=100}]``)

        For dict format the key ``step`` is optional (default value is 1).
    restrict_prefix_length : bool (optional)
        By default, class won't allow prefixes with prefix length
        below 112. This limits number of addresses to 2^16 or 65536.
        The reason is that expansion (converting prefix to list of
        individual adressess) would require computational and memory
        resources. This check can be turned off, but user then takes
        responsibility.
    """

    _SUPPORTED_NON_LIST_TYPES = (
        str,
        ipaddress.IPv6Address,
        ipaddress.IPv6Network,
    )
    _VERSION = 6
    _PREFIX_MAXLEN = 128

    def addresses_as_list(self):
        """Return addresses in form of sorted list.

        Returns
        ------
        list(ipaddress.IPv6Address)
            IP addresses.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        addresses = super().addresses_as_list()
        addresses = list(map(ipaddress.ip_address, addresses))
        addresses.sort()
        return addresses

    def hosts_as_list(self):
        """Return usable hosts in form of sorted list.

        This method differs from ``addresses_as_list`` as it does
        **not** include network address (Subnet-Router anycast address) when prefix
        length (PF) is 126 or lower. For PF 127, network address is included.
        For PF 128, empty list is returned.

        Note: Broadcast address is included by default, as in IPv6 broadcast
        is replaced by multicast and as such it is considered usable address.

        Returns
        ------
        list(ipaddress.IPv6Address)
            Hosts.

        Raises
        ------
        AssertionError
            In case prefix contains >= 2^16 addresses and restricted
            mode is enabled.
        """

        hosts = super().hosts_as_list()
        hosts = list(map(ipaddress.ip_address, hosts))
        hosts.sort()
        return hosts

    def address_generator(self):
        """Return address generator.

        You can use this as::

            for ipaddr in address_generator():
                print(ipaddr)

        Returns
        ------
        generator(ipaddress.IPv6Address)
            IP addresses generator.
        """

        for net in self._addr_list:
            network = ipaddress.ip_network(net)

            if network.prefixlen <= 126:
                yield network.network_address
                for addr in network.hosts():
                    yield addr
            elif network.prefixlen == 127:
                yield network.network_address
                yield network.broadcast_address
            else:
                yield network.network_address

    def host_generator(self):
        """Return host generator.

        You can use this as::

            for host in host_generator():
                print(host)

        Returns
        ------
        generator(ipaddress.IPv6Address)
            IP host generator.
        """

        for net in self._addr_list:
            network = ipaddress.ip_network(net)

            if network.prefixlen <= 127:
                for addr in network.hosts():
                    yield addr
            else:
                yield network.network_address
