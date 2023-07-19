"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Unit tests of ipaddresses module.
"""

import ipaddress

import pytest

from lbr_testsuite.packet_crafter import ipaddresses, random_types

from .conftest import _is_equal


def _get_generator_output(addr):
    """Put generator output into list and return it."""

    ip_gen = []
    host_gen = []
    for ip in addr.address_generator():
        ip_gen.append(ip)
    for host in addr.host_generator():
        host_gen.append(host)

    return ip_gen, host_gen


def test_base_class_cannot_be_used():
    """Check ipaddresses.BaseIPAddresses cannot be used on it's own."""
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses("10.0.0.0")
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses("10.0.0.0/24")
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses("aaaa::")
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses("aaaa::/120")
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses(ipaddress.ip_address("10.0.0.0"))
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses(ipaddress.ip_network("10.0.0.0/24"))
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses(ipaddress.ip_address("aaaa::"))
    with pytest.raises(AssertionError):
        ipaddresses.BaseIPAddresses(ipaddress.ip_network("aaaa::/120"))


def test_ipv4_bad_testing_data():
    """Check ipaddresses.IPv4Addresses raises error when bad input is inserted."""
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses(123)
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses((1, 2))
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses("AAAA::")
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses(ipaddress.IPv6Address("AAAA::"))
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses("AAAA::/120")
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses(ipaddress.IPv6Network("AAAA::/120"))


def test_ipv6_bad_testing_data():
    """Check ipaddresses.IPv6Addresses raises error when bad input is inserted."""
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses(123)
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses((1, 2))
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses("10.0.0.0")
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses(ipaddress.IPv4Address("10.0.0.0"))
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses("10.0.0.0/24")
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses(ipaddress.IPv4Network("10.0.0.0/24"))


def test_ipv4_single_address():
    """Check correct behavior of ipaddresses.IPv4Addresses when single IPv4 address is set."""

    # check both 'str' and 'ipaddress.IPv4Address' format
    for testing_data in ["10.0.0.0", ipaddress.IPv4Address("10.0.0.0")]:
        addr = ipaddresses.IPv4Addresses(testing_data)
        assert addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert not addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 1
        assert addr.hosts_count() == 1
        assert addr.addresses_as_list() == [ipaddress.IPv4Address(testing_data)]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_single_address():
    """Check correct behavior of ipaddresses.IPv6Addresses when single IPv6 address is set."""

    # check both 'str' and 'ipaddress.IPv6Address' format
    for testing_data in ["aaaa::", ipaddress.IPv6Address("aaaa::")]:
        addr = ipaddresses.IPv6Addresses(testing_data)
        assert addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert not addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 1
        assert addr.hosts_count() == 1
        assert addr.addresses_as_list() == [ipaddress.IPv6Address(testing_data)]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_single_prefix():
    """Check correct behavior of ipaddresses.IPv4Addresses when single IPv4 prefix is set."""
    for testing_data in ["10.0.0.0/24", ipaddress.IPv4Network("10.0.0.0/24")]:
        addr = ipaddresses.IPv4Addresses(testing_data)
        assert not addr.is_single_ip()
        assert addr.is_single_prefix()
        assert not addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 256
        assert addr.hosts_count() == 254
        assert addr.addresses_as_list() == [
            ipaddress.IPv4Network(testing_data).network_address,
            *list(ipaddress.IPv4Network(testing_data).hosts()),
            ipaddress.IPv4Network(testing_data).broadcast_address,
        ]
        assert addr.hosts_as_list() == list(ipaddress.IPv4Network(testing_data).hosts())
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_single_prefix():
    """Check correct behavior of ipaddresses.IPv6Addresses when single IPv6 prefix is set."""
    for testing_data in ["aaaa::/120", ipaddress.IPv6Network("aaaa::/120")]:
        addr = ipaddresses.IPv6Addresses(testing_data)
        assert not addr.is_single_ip()
        assert addr.is_single_prefix()
        assert not addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 256
        assert addr.hosts_count() == 255
        assert addr.addresses_as_list() == [
            ipaddress.IPv6Network(testing_data).network_address,
            *list(ipaddress.IPv6Network(testing_data).hosts()),
        ]
        assert addr.hosts_as_list() == list(ipaddress.IPv6Network(testing_data).hosts())
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_dict_without_step():
    """Check correct behavior of ipaddresses.IPv4Addresses when dict
    (without 'step' keyword) is set.
    """
    for testing_data in [
        {"first": "10.0.0.0", "count": 10},
        {"first": ipaddress.IPv4Address("10.0.0.0"), "count": 10},
    ]:
        addr = ipaddresses.IPv4Addresses(testing_data)

        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 10
        assert addr.hosts_count() == 10
        assert addr.addresses_as_list() == [
            ipaddress.IPv4Address("10.0.0.0"),
            ipaddress.IPv4Address("10.0.0.1"),
            ipaddress.IPv4Address("10.0.0.2"),
            ipaddress.IPv4Address("10.0.0.3"),
            ipaddress.IPv4Address("10.0.0.4"),
            ipaddress.IPv4Address("10.0.0.5"),
            ipaddress.IPv4Address("10.0.0.6"),
            ipaddress.IPv4Address("10.0.0.7"),
            ipaddress.IPv4Address("10.0.0.8"),
            ipaddress.IPv4Address("10.0.0.9"),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_dict_without_step():
    """Check correct behavior of ipaddresses.IPv6Addresses when dict
    (without 'step' keyword) is set.
    """
    for testing_data in [
        {"first": "aaaa::", "count": 10},
        {"first": ipaddress.IPv6Address("aaaa::"), "count": 10},
    ]:
        addr = ipaddresses.IPv6Addresses(testing_data)

        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 10
        assert addr.hosts_count() == 10
        assert addr.addresses_as_list() == [
            ipaddress.IPv6Address("aaaa::"),
            ipaddress.IPv6Address("aaaa::1"),
            ipaddress.IPv6Address("aaaa::2"),
            ipaddress.IPv6Address("aaaa::3"),
            ipaddress.IPv6Address("aaaa::4"),
            ipaddress.IPv6Address("aaaa::5"),
            ipaddress.IPv6Address("aaaa::6"),
            ipaddress.IPv6Address("aaaa::7"),
            ipaddress.IPv6Address("aaaa::8"),
            ipaddress.IPv6Address("aaaa::9"),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_dict_with_step():
    """Check correct behavior of ipaddresses.IPv4Addresses when dict
    (with 'step' keyword) is set.
    """
    for testing_data in [
        {"first": "10.0.0.0", "count": 10, "step": 20},
        {"first": ipaddress.IPv4Address("10.0.0.0"), "count": 10, "step": 20},
    ]:
        addr = ipaddresses.IPv4Addresses(testing_data)
        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 10
        assert addr.hosts_count() == 10
        assert addr.addresses_as_list() == [
            ipaddress.IPv4Address("10.0.0.0"),
            ipaddress.IPv4Address("10.0.0.20"),
            ipaddress.IPv4Address("10.0.0.40"),
            ipaddress.IPv4Address("10.0.0.60"),
            ipaddress.IPv4Address("10.0.0.80"),
            ipaddress.IPv4Address("10.0.0.100"),
            ipaddress.IPv4Address("10.0.0.120"),
            ipaddress.IPv4Address("10.0.0.140"),
            ipaddress.IPv4Address("10.0.0.160"),
            ipaddress.IPv4Address("10.0.0.180"),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_dict_with_step():
    """Check correct behavior of ipaddresses.IPv6Addresses when dict
    (with 'step' keyword) is set.
    """
    for testing_data in [
        {"first": "aaaa::", "count": 10, "step": 20},
        {"first": ipaddress.IPv6Address("aaaa::"), "count": 10, "step": 20},
    ]:
        addr = ipaddresses.IPv6Addresses(testing_data)
        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 10
        assert addr.hosts_count() == 10
        assert addr.addresses_as_list() == [
            ipaddress.IPv6Address("aaaa::"),
            ipaddress.IPv6Address("aaaa::14"),
            ipaddress.IPv6Address("aaaa::28"),
            ipaddress.IPv6Address("aaaa::3C"),
            ipaddress.IPv6Address("aaaa::50"),
            ipaddress.IPv6Address("aaaa::64"),
            ipaddress.IPv6Address("aaaa::78"),
            ipaddress.IPv6Address("aaaa::8C"),
            ipaddress.IPv6Address("aaaa::A0"),
            ipaddress.IPv6Address("aaaa::B4"),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_dict_wrong_testing_datas():
    """Check ipaddresses.IPv4Addresses raises error when dict has wrong keys/values."""
    # missing 'count' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses({"first": "10.0.0.0"})
    # misspelled 'first' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses({"ffirst": "10.0.0.0", "count": 10})
    # misspelled 'count' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses({"first": "10.0.0.0", "countt": 10})
    # IPv6 is used
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses({"first": "AAAA::", "count": 10})
    # wrong value type for 'first' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses({"first": 10, "count": 10})


def test_ipv6_dict_wrong_testing_datas():
    """Check ipaddresses.IPv6Addresses raises error when dict has wrong keys/values."""
    # missing 'count' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses({"first": "aaaa::"})
    # misspelled 'first' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses({"ffirst": "aaaa::", "count": 10})
    # misspelled 'count' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses({"first": "aaaa::", "countt": 10})
    # IPv6 is used
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses({"first": "10.0.0.0", "count": 10})
    # wrong value type for 'first' key
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses({"first": 10, "count": 10})


def test_ipv4_random():
    """Check correct behavior of ipaddresses.IPv4Addresses when random_types.RandomIP is set."""
    testing_data = random_types.RandomIP(5, seed=123)
    addr = ipaddresses.IPv4Addresses(testing_data)
    assert not addr.is_single_ip()
    assert not addr.is_single_prefix()
    assert addr.is_ip_list()
    assert addr.is_random()
    assert addr.addresses_count() == 5
    assert addr.hosts_count() == 5
    assert addr.addresses_as_list() == [
        ipaddress.IPv4Address("35.82.91.82"),
        ipaddress.IPv4Address("53.66.186.34"),
        ipaddress.IPv4Address("66.113.28.21"),
        ipaddress.IPv4Address("69.148.119.107"),
        ipaddress.IPv4Address("184.135.155.222"),
    ]
    assert addr.hosts_as_list() == addr.addresses_as_list()
    ip_gen, host_gen = _get_generator_output(addr)
    assert _is_equal(ip_gen, addr.addresses_as_list())
    assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_random():
    """Check correct behavior of ipaddresses.IPv6Addresses when random_types.RandomIP is set."""
    testing_data = random_types.RandomIP(5, seed=123)
    addr = ipaddresses.IPv6Addresses(testing_data)
    assert not addr.is_single_ip()
    assert not addr.is_single_prefix()
    assert addr.is_ip_list()
    assert addr.is_random()
    assert addr.addresses_count() == 5
    assert addr.hosts_count() == 5
    assert addr.addresses_as_list() == [
        ipaddress.IPv6Address("2293:202c:28df:a298:d49:6d4c:da22:594f"),
        ipaddress.IPv6Address("573e:8d77:550a:e889:8ff4:1e8e:8944:897c"),
        ipaddress.IPv6Address("610e:4ad5:9c4:7055:dff4:9490:e6b4:f832"),
        ipaddress.IPv6Address("c4da:537c:1651:ddae:4486:7db4:d67:b366"),
        ipaddress.IPv6Address("d6a8:2a95:1b92:3e0a:443c:def4:6840:ff07"),
    ]
    assert addr.hosts_as_list() == addr.addresses_as_list()
    ip_gen, host_gen = _get_generator_output(addr)
    assert _is_equal(ip_gen, addr.addresses_as_list())
    assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_list():
    """Check correct behavior of ipaddresses.IPv4Addresses when list is set."""
    for testing_data in [
        ["10.0.0.1", "10.0.0.2", "10.0.0.3", "10.0.0.4"],
        [
            ipaddress.IPv4Address("10.0.0.1"),
            ipaddress.IPv4Address("10.0.0.2"),
            ipaddress.IPv4Address("10.0.0.3"),
            ipaddress.IPv4Address("10.0.0.4"),
        ],
    ]:
        addr = ipaddresses.IPv4Addresses(testing_data)
        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 4
        assert addr.hosts_count() == 4
        assert addr.addresses_as_list() == [
            ipaddress.IPv4Address(testing_data[0]),
            ipaddress.IPv4Address(testing_data[1]),
            ipaddress.IPv4Address(testing_data[2]),
            ipaddress.IPv4Address(testing_data[3]),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_list():
    """Check correct behavior of ipaddresses.IPv6Addresses when list is set."""
    for testing_data in [
        ["aaaa::1", "aaaa::2", "aaaa::3", "aaaa::4"],
        [
            ipaddress.IPv6Address("aaaa::1"),
            ipaddress.IPv6Address("aaaa::2"),
            ipaddress.IPv6Address("aaaa::3"),
            ipaddress.IPv6Address("aaaa::4"),
        ],
    ]:
        addr = ipaddresses.IPv6Addresses(testing_data)
        assert not addr.is_single_ip()
        assert not addr.is_single_prefix()
        assert addr.is_ip_list()
        assert not addr.is_random()
        assert addr.addresses_count() == 4
        assert addr.hosts_count() == 4
        assert addr.addresses_as_list() == [
            ipaddress.IPv6Address(testing_data[0]),
            ipaddress.IPv6Address(testing_data[1]),
            ipaddress.IPv6Address(testing_data[2]),
            ipaddress.IPv6Address(testing_data[3]),
        ]
        assert addr.hosts_as_list() == addr.addresses_as_list()
        ip_gen, host_gen = _get_generator_output(addr)
        assert _is_equal(ip_gen, addr.addresses_as_list())
        assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv4_restricted_range():
    """Ensure ipaddresses.IPv4Addresses raises error when input is bigger than allowed limit."""
    # Prefix length /16 (2^16 addresses) is max allowed limit by default
    ipaddresses.IPv4Addresses("10.0.0.0/16").addresses_as_list()
    ipaddresses.IPv4Addresses("10.0.0.0/16").hosts_as_list()
    ipaddresses.IPv4Addresses(ipaddress.IPv4Network("10.0.0.0/16")).addresses_as_list()
    ipaddresses.IPv4Addresses(ipaddress.IPv4Network("10.0.0.0/16")).hosts_as_list()

    # Error isn't raised until addresses_as_list() or hosts_as_list() method is called
    addr = ipaddresses.IPv4Addresses(list(ipaddress.IPv4Network("10.0.0.0/15").hosts()))

    # Ensure generators do not raise any error
    ip_gen, host_gen = _get_generator_output(addr)

    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses(
            list(ipaddress.IPv4Network("10.0.0.0/15").hosts())
        ).addresses_as_list()
    with pytest.raises(AssertionError):
        ipaddresses.IPv4Addresses(
            list(ipaddress.IPv4Network("10.0.0.0/15").hosts())
        ).hosts_as_list()

    for pl in range(1, 16):
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(f"128.0.0.0/{pl}").addresses_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(f"128.0.0.0/{pl}").hosts_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(ipaddress.IPv4Network(f"128.0.0.0/{pl}")).addresses_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(ipaddress.IPv4Network(f"128.0.0.0/{pl}")).hosts_as_list()

    for count in range(16, 32):
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses({"first": "1.0.0.0", "count": 2**count + 1})
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses({"first": "1.0.0.0", "count": 2**count + 1, "step": 2})
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(
                {"first": ipaddress.IPv4Address("1.0.0.0"), "count": 2**count + 1}
            )
        with pytest.raises(AssertionError):
            ipaddresses.IPv4Addresses(
                {"first": ipaddress.IPv4Address("1.0.0.0"), "count": 2**count + 1, "step": 2}
            )


def test_ipv6_restricted_range():
    """Ensure ipaddresses.IPv6Addresses raises error when input is bigger than allowed limit."""
    # Prefix length /112 (2^16 addresses) is max allowed limit by default
    ipaddresses.IPv6Addresses("aaaa::/112").addresses_as_list()
    ipaddresses.IPv6Addresses("aaaa::/112").hosts_as_list()
    ipaddresses.IPv6Addresses(ipaddress.IPv6Network("aaaa::/112")).addresses_as_list()
    ipaddresses.IPv6Addresses(ipaddress.IPv6Network("aaaa::/112")).hosts_as_list()

    # Error isn't raised until addresses_as_list() or hosts_as_list() method is called
    addr = ipaddresses.IPv6Addresses(list(ipaddress.IPv6Network("aaaa::/111").hosts()))

    # Ensure generators do not raise any errors
    ip_gen, host_gen = _get_generator_output(addr)

    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses(
            list(ipaddress.IPv6Network("aaaa::/111").hosts())
        ).addresses_as_list()
    with pytest.raises(AssertionError):
        ipaddresses.IPv6Addresses(list(ipaddress.IPv6Network("aaaa::/111").hosts())).hosts_as_list()

    for pl in range(1, 112):
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(f"8000::/{pl}").addresses_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(f"8000::/{pl}").hosts_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(ipaddress.IPv6Network(f"8000::/{pl}")).addresses_as_list()
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(ipaddress.IPv6Network(f"8000::/{pl}")).hosts_as_list()

    for count in range(16, 32):
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses({"first": "aaaa::", "count": 2**count + 1})
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses({"first": "aaaa::", "count": 2**count + 1, "step": 2})
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(
                {"first": ipaddress.IPv6Address("aaaa::"), "count": 2**count + 1}
            )
        with pytest.raises(AssertionError):
            ipaddresses.IPv6Addresses(
                {"first": ipaddress.IPv6Address("aaaa::"), "count": 2**count + 1, "step": 2}
            )


def test_ipv4_unrestricted_range():
    """Ensure ipaddresses.IPv4Addresses doesn't raises error when input size limit is disabled."""
    ipaddresses.IPv4Addresses(
        list(ipaddress.IPv4Network("10.0.0.0/15").hosts()),
        restrict_prefix_length=False,
    ).addresses_as_list()
    ipaddresses.IPv4Addresses(
        list(ipaddress.IPv4Network("10.0.0.0/15").hosts()),
        restrict_prefix_length=False,
    ).hosts_as_list()

    ipaddresses.IPv4Addresses("128.0.0.0/15", restrict_prefix_length=False).addresses_as_list()
    ipaddresses.IPv4Addresses("128.0.0.0/15", restrict_prefix_length=False).hosts_as_list()
    ipaddresses.IPv4Addresses(
        ipaddress.IPv4Network("128.0.0.0/15"), restrict_prefix_length=False
    ).addresses_as_list()
    ipaddresses.IPv4Addresses(
        ipaddress.IPv4Network("128.0.0.0/15"), restrict_prefix_length=False
    ).hosts_as_list()

    ipaddresses.IPv4Addresses(
        {"first": "1.0.0.0", "count": 2**16 + 1},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv4Addresses(
        {"first": "1.0.0.0", "count": 2**16 + 1, "step": 2},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv4Addresses(
        {"first": ipaddress.IPv4Address("1.0.0.0"), "count": 2**16 + 1},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv4Addresses(
        {"first": ipaddress.IPv4Address("1.0.0.0"), "count": 2**16 + 1, "step": 2},
        restrict_prefix_length=False,
    )


def test_ipv6_unrestricted_range():
    """Ensure ipaddresses.IPv6Addresses doesn't raises error when input size limit is disabled."""
    ipaddresses.IPv6Addresses(
        list(ipaddress.IPv6Network("aaaa::/111").hosts()),
        restrict_prefix_length=False,
    ).addresses_as_list()
    ipaddresses.IPv6Addresses(
        list(ipaddress.IPv6Network("aaaa::/111").hosts()),
        restrict_prefix_length=False,
    ).hosts_as_list()

    ipaddresses.IPv6Addresses("8000::/111", restrict_prefix_length=False).addresses_as_list()
    ipaddresses.IPv6Addresses("8000::/111", restrict_prefix_length=False).hosts_as_list()
    ipaddresses.IPv6Addresses(
        ipaddress.IPv6Network("8000::/111"), restrict_prefix_length=False
    ).addresses_as_list()
    ipaddresses.IPv6Addresses(
        ipaddress.IPv6Network("8000::/111"), restrict_prefix_length=False
    ).hosts_as_list()

    ipaddresses.IPv6Addresses(
        {"first": "8000::", "count": 2**16 + 1},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv6Addresses(
        {"first": "8000::", "count": 2**16 + 1, "step": 2},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv6Addresses(
        {"first": ipaddress.IPv6Address("8000::"), "count": 2**16 + 1},
        restrict_prefix_length=False,
    )
    ipaddresses.IPv6Addresses(
        {"first": ipaddress.IPv6Address("8000::"), "count": 2**16 + 1, "step": 2},
        restrict_prefix_length=False,
    )


def test_ipv4_complex_list():
    """Check correct behavior of ipaddresses.IPv4Addresses when list of all allowed types is set."""
    testing_data = [
        "10.0.0.0",  # 1 address
        ipaddress.IPv4Address("11.0.0.0"),  # 1 address
        "12.0.0.0/30",  # 4 addresses, 2 usable hosts
        ipaddress.IPv4Network("13.0.0.0/30"),  # 4 addresses, 2 usable hosts
        dict(first="14.0.0.0", count=3),  # 3 addresses
        dict(first=ipaddress.IPv4Address("15.0.0.0"), count=3, step=2**24),  # 3 addresses
        random_types.RandomIP(2, seed=123),  # 2 addresses
    ]
    addr = ipaddresses.IPv4Addresses(testing_data)

    assert not addr.is_single_ip()
    assert not addr.is_single_prefix()
    assert addr.is_ip_list()
    assert addr.is_random()
    assert addr.addresses_count() == 18  # 1 + 1 + 4 + 4 + 3 + 3 + 2 (corresponds to items in list)
    assert addr.hosts_count() == 14  # 1 + 1 + 2 + 2 + 3 + 3 + 2 (corresponds to items in list)

    assert addr.addresses_as_list() == [
        ipaddress.IPv4Address("10.0.0.0"),
        ipaddress.IPv4Address("11.0.0.0"),
        ipaddress.IPv4Address("12.0.0.0"),
        ipaddress.IPv4Address("12.0.0.1"),
        ipaddress.IPv4Address("12.0.0.2"),
        ipaddress.IPv4Address("12.0.0.3"),
        ipaddress.IPv4Address("13.0.0.0"),
        ipaddress.IPv4Address("13.0.0.1"),
        ipaddress.IPv4Address("13.0.0.2"),
        ipaddress.IPv4Address("13.0.0.3"),
        ipaddress.IPv4Address("14.0.0.0"),
        ipaddress.IPv4Address("14.0.0.1"),
        ipaddress.IPv4Address("14.0.0.2"),
        ipaddress.IPv4Address("15.0.0.0"),
        ipaddress.IPv4Address("16.0.0.0"),
        ipaddress.IPv4Address("17.0.0.0"),
        ipaddress.IPv4Address("69.148.119.107"),
        ipaddress.IPv4Address("184.135.155.222"),
    ]

    assert addr.hosts_as_list() == [
        ipaddress.IPv4Address("10.0.0.0"),
        ipaddress.IPv4Address("11.0.0.0"),
        ipaddress.IPv4Address("12.0.0.1"),
        ipaddress.IPv4Address("12.0.0.2"),
        ipaddress.IPv4Address("13.0.0.1"),
        ipaddress.IPv4Address("13.0.0.2"),
        ipaddress.IPv4Address("14.0.0.0"),
        ipaddress.IPv4Address("14.0.0.1"),
        ipaddress.IPv4Address("14.0.0.2"),
        ipaddress.IPv4Address("15.0.0.0"),
        ipaddress.IPv4Address("16.0.0.0"),
        ipaddress.IPv4Address("17.0.0.0"),
        ipaddress.IPv4Address("69.148.119.107"),
        ipaddress.IPv4Address("184.135.155.222"),
    ]

    ip_gen, host_gen = _get_generator_output(addr)
    assert _is_equal(ip_gen, addr.addresses_as_list())
    assert _is_equal(host_gen, addr.hosts_as_list())


def test_ipv6_complex_list():
    """Check correct behavior of ipaddresses.IPv6Addresses when list of all allowed types is set."""
    testing_data = [
        "aaa0::",  # 1 address
        ipaddress.IPv6Address("aaa1::"),  # 1 address
        "aaa2::/126",  # 4 addresses, 3 usable hosts
        ipaddress.IPv6Network("aaa3::/126"),  # 3 usable hosts
        dict(first="aaa4::", count=3),  # 3 addresses
        dict(first=ipaddress.IPv6Address("aaa5::"), count=3, step=2**112),  # 3 addresses
        random_types.RandomIP(2, seed=123),  # 2 addresses
    ]
    addr = ipaddresses.IPv6Addresses(testing_data)

    assert not addr.is_single_ip()
    assert not addr.is_single_prefix()
    assert addr.is_ip_list()
    assert addr.is_random()
    assert addr.addresses_count() == 18  # 1 + 1 + 4 + 4 + 3 + 3 + 2 (corresponds to items in list)
    assert addr.hosts_count() == 16  # 1 + 1 + 3 + 3 + 3 + 3 + 2 (corresponds to items in list)

    assert addr.addresses_as_list() == [
        ipaddress.IPv6Address("aaa0::"),
        ipaddress.IPv6Address("aaa1::"),
        ipaddress.IPv6Address("aaa2::0"),
        ipaddress.IPv6Address("aaa2::1"),
        ipaddress.IPv6Address("aaa2::2"),
        ipaddress.IPv6Address("aaa2::3"),
        ipaddress.IPv6Address("aaa3::0"),
        ipaddress.IPv6Address("aaa3::1"),
        ipaddress.IPv6Address("aaa3::2"),
        ipaddress.IPv6Address("aaa3::3"),
        ipaddress.IPv6Address("aaa4::0"),
        ipaddress.IPv6Address("aaa4::1"),
        ipaddress.IPv6Address("aaa4::2"),
        ipaddress.IPv6Address("aaa5::"),
        ipaddress.IPv6Address("aaa6::"),
        ipaddress.IPv6Address("aaa7::"),
        ipaddress.IPv6Address("c4da:537c:1651:ddae:4486:7db4:d67:b366"),
        ipaddress.IPv6Address("d6a8:2a95:1b92:3e0a:443c:def4:6840:ff07"),
    ]

    assert addr.hosts_as_list() == [
        ipaddress.IPv6Address("aaa0::"),
        ipaddress.IPv6Address("aaa1::"),
        ipaddress.IPv6Address("aaa2::1"),
        ipaddress.IPv6Address("aaa2::2"),
        ipaddress.IPv6Address("aaa2::3"),
        ipaddress.IPv6Address("aaa3::1"),
        ipaddress.IPv6Address("aaa3::2"),
        ipaddress.IPv6Address("aaa3::3"),
        ipaddress.IPv6Address("aaa4::0"),
        ipaddress.IPv6Address("aaa4::1"),
        ipaddress.IPv6Address("aaa4::2"),
        ipaddress.IPv6Address("aaa5::"),
        ipaddress.IPv6Address("aaa6::"),
        ipaddress.IPv6Address("aaa7::"),
        ipaddress.IPv6Address("c4da:537c:1651:ddae:4486:7db4:d67:b366"),
        ipaddress.IPv6Address("d6a8:2a95:1b92:3e0a:443c:def4:6840:ff07"),
    ]

    ip_gen, host_gen = _get_generator_output(addr)
    assert _is_equal(ip_gen, addr.addresses_as_list())
    assert _is_equal(host_gen, addr.hosts_as_list())
