"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Unit tests of ports module.
"""

import pytest

from lbr_testsuite.packet_crafter import ports, random_types


def _get_generator_output(port):
    """Put generator output into list and return it."""

    port_gen = []
    for p in port.port_generator():
        port_gen.append(p)

    return port_gen


def test_bad_testing_data():
    """Check ports.L4Ports raises error when bad testing data is inserted."""
    with pytest.raises(AssertionError):
        ports.L4Ports("a")
    with pytest.raises(AssertionError):
        ports.L4Ports(1.22)
    with pytest.raises(AssertionError):
        ports.L4Ports(dict())
    with pytest.raises(AssertionError):
        ports.L4Ports(-1)
    with pytest.raises(AssertionError):
        ports.L4Ports(2**16)
    with pytest.raises(AssertionError):
        ports.L4Ports((2, 2**16))
    with pytest.raises(AssertionError):
        ports.L4Ports((-1, 1))
    with pytest.raises(AssertionError):
        ports.L4Ports([-1])
    with pytest.raises(AssertionError):
        ports.L4Ports([2**16])
    with pytest.raises(AssertionError):
        ports.L4Ports((100, 99))


def test_single_port_0():
    """Check correct behavior of ports.L4Ports when single port is set."""
    testing_data = 0
    port = ports.L4Ports(testing_data)
    assert port.is_single_port()
    assert not port.is_port_range()
    assert not port.is_port_list()
    assert not port.is_random()
    assert port.ports() == testing_data
    assert port.count() == 1
    assert port.ports_as_list() == [testing_data]
    assert port.ports_as_range() == (testing_data, testing_data)
    assert set(_get_generator_output(port)) == set(port.ports_as_list())


def test_single_port_65535():
    """Check correct behavior of ports.L4Ports when single port is set."""
    testing_data = 65535
    port = ports.L4Ports(testing_data)
    assert port.is_single_port()
    assert not port.is_port_range()
    assert not port.is_port_list()
    assert not port.is_random()
    assert port.ports() == testing_data
    assert port.count() == 1
    assert port.ports_as_list() == [testing_data]
    assert port.ports_as_range() == (testing_data, testing_data)
    assert set(_get_generator_output(port)) == set(port.ports_as_list())


def test_port_range():
    """Check correct behavior of ports.L4Ports when port range is set."""
    testing_data = (0, 65535)
    port = ports.L4Ports(testing_data)
    assert not port.is_single_port()
    assert port.is_port_range()
    assert not port.is_port_list()
    assert not port.is_random()
    assert port.ports() == testing_data
    assert port.count() == 65536
    assert port.ports_as_list() == list(range(65536))
    assert port.ports_as_range() == testing_data
    assert set(_get_generator_output(port)) == set(port.ports_as_list())


def test_port_list():
    """Check correct behavior of ports.L4Ports when port list is set."""
    testing_data = list(range(65536))
    port = ports.L4Ports(testing_data)
    assert not port.is_single_port()
    assert not port.is_port_range()
    assert port.is_port_list()
    assert not port.is_random()
    assert port.ports() == testing_data
    assert port.count() == 65536
    assert port.ports_as_list() == testing_data
    assert port.ports_as_range() == (0, 65535)
    assert set(_get_generator_output(port)) == set(port.ports_as_list())


def test_random_port():
    """Check correct behavior of ports.L4Ports when random_types.RandomPort is set."""
    testing_data = random_types.RandomPort(10, seed=123)
    port = ports.L4Ports(testing_data)
    assert not port.is_single_port()
    assert not port.is_port_range()
    assert port.is_port_list()
    assert port.is_random()
    assert (
        port.ports()
        == port.ports_as_list()
        == [
            5000,
            6863,
            11427,
            14116,
            34937,
            35084,
            43541,
            44669,
            49692,
            53377,
        ]
    )
    assert port.count() == 10
    with pytest.raises(AssertionError):
        port.ports_as_range()
    assert set(_get_generator_output(port)) == set(port.ports_as_list())


def test_port_list_count():
    """Check correct behavior of count() for list with multiple items."""
    testing_data = [111, (0, 1000), (1001, 2001), 222]
    port = ports.L4Ports(testing_data)
    assert port.count() == 1 + 1001 + 1001 + 1


def test_port_list_to_range():
    """Check conversion of suitable list to range."""
    testing_data = [0, 3, 2, 1, 4]
    port = ports.L4Ports(testing_data)
    assert port.ports_as_range() == (0, 4)


def test_port_list_to_range_complex():
    """Check conversion of complex suitable list to range."""
    testing_data = [0, 3, 2, (5, 6), 1, 4, (7, 9)]
    port = ports.L4Ports(testing_data)
    assert port.ports_as_range() == (0, 9)


def test_port_bad_list_to_range():
    """Check conversion of unsuitable list to range fails."""
    testing_data = [0, 3, 2, (5, 6)]
    port = ports.L4Ports(testing_data)
    with pytest.raises(AssertionError):
        port.ports_as_range()


def test_port_expand_list():
    """Check correct behavior of ports_as_list() for list with tuples."""
    testing_data = [111, (10, 15), 222]
    port = ports.L4Ports(testing_data)
    assert port.ports_as_list() == [111, 10, 11, 12, 13, 14, 15, 222]


def test_string_conversion():
    """Check correct conversion to string"""

    port_single = ports.L4Ports(120)
    assert str(port_single) == "120"

    port_list = ports.L4Ports([10, 11, 12, 15])
    assert str(port_list) == "[10, 11, 12, 15]"

    port_range = ports.L4Ports((10, 20))
    assert str(port_range) == "10-20"


def test_member():
    """Check correct testing for port membership within L4Ports instance"""

    port_single = ports.L4Ports(120)
    assert port_single.member(120)

    port_list = ports.L4Ports([10, 20, 30])
    assert port_list.member(10)
    assert port_list.member(20)
    assert port_list.member(30)

    port_range = ports.L4Ports((10, 20))
    for i in range(10, 21):
        assert port_range.member(i)
