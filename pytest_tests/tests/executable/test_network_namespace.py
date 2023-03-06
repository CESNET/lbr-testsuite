"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of executable module features and sysctl commands used with
network namespaces.
"""

import logging
import pathlib
import socket
import time

import pyroute2
import pytest

from lbr_testsuite.common import sysctl
from lbr_testsuite.executable import executable


@pytest.fixture
def _testing_namespace(require_root):
    netns = "lbr_testsuite_ns"

    pyroute2.netns.create(netns)
    yield netns
    pyroute2.netns.remove(netns)


def _get_ip(ifc, netns=None):
    if netns:
        ip = pyroute2.NetNS(netns)
    else:
        ip = pyroute2.IPRoute()

    address = ip.get_addr(label=ifc, family=socket.AF_INET)
    if len(address) == 0:
        return None

    address = dict(address[0]["attrs"])
    return address["IFA_ADDRESS"]


def _flip_value(value):
    v = int(value)
    assert v in [0, 1], "value has to be 0 or 1"

    return str(1 - v)


def _set_ns_loobpack_up(ns):
    pyroute2.NetNS(ns).link("set", ifname="lo", state="up")


def test_set_ip_in_namespace(_testing_namespace):
    """Test that a simple command is executed under a namespace.

    - store IP address of loopback interface within and outside of
    the testing namespace (there should be no IP address within
    the namespace),
    - set a testing IP address on the loopback within the namespace,
    - check that the IP is set correctly and IP of loopback outside
    the namespace has not been changed.
    """

    TEST_IP = "10.0.0.1"

    default_lo = _get_ip("lo")
    ns_lo = _get_ip("lo", _testing_namespace)

    assert (
        ns_lo is None
    ), f"expecting no address on loopback interface in namespace {_testing_namespace}"

    executable.Tool(
        ["ip", "addr", "add", TEST_IP, "dev", "lo"],
        netns=_testing_namespace,
    ).run()

    assert default_lo == _get_ip("lo")
    assert (
        _get_ip("lo", _testing_namespace) == TEST_IP
    ), f"IP address of loopback in namespace {_testing_namespace} was not changed"


def test_set_ping_in_namespace(_testing_namespace):
    """Test that a simple daemon-like command is executed under
    a namespace.

    - bring loopback within the testing namespace up (this action
    automatically assigns 127.0.0.1 IP address),
    - start ping to the localhost address,
    - check that ping is running,
    - stop the ping command,
    - if ping failed an exception is raised (test fails).
    """

    LO_ADDRESS = "127.0.0.1"
    _set_ns_loobpack_up(_testing_namespace)

    assert (
        _get_ip("lo", _testing_namespace) == LO_ADDRESS
    ), f"expecting address {LO_ADDRESS} on loopback interface in namespace {_testing_namespace}"

    ping = executable.Daemon(["ping", "127.0.0.1"], netns=_testing_namespace, sigterm_ok=True)
    ping.start()

    time.sleep(1)

    assert ping.is_running()

    ping.stop()


def test_sysctl_in_namespace(_testing_namespace):
    """Test that variable changed via sysctl affects only namespace.

    - tested variable is net.ipv6.conf.default.disable_ipv6,
    - first retrieve current values (within and outside of the testing
    namespace),
    - flip current value within the namespace; check expected values
    (test that value is changed within the namespace),
    - set value within the namespace to the opposite value than outside
    the namespace (test that values differs - i.e. not affecting each
    other).
    """

    TEST_VAR = "net.ipv6.conf.default.disable_ipv6"

    def _get_sys_vals():
        sys = sysctl.sysctl_get(TEST_VAR)[0]
        ns = sysctl.sysctl_get(TEST_VAR, netns=_testing_namespace)[0]
        return sys, ns

    system_val, ns_val = _get_sys_vals()

    # Test change of the value in namespace
    sysctl.sysctl_set(TEST_VAR, _flip_value(ns_val), netns=_testing_namespace)
    system_val_new, ns_val_new = _get_sys_vals()
    assert system_val == system_val_new, "system value changed"
    assert _flip_value(ns_val) == ns_val_new, "value in namespace was not changed as expected"

    # Test different values in system and namespace
    sysctl.sysctl_set(TEST_VAR, _flip_value(system_val), netns=_testing_namespace)
    system_val_new, ns_val_new = _get_sys_vals()
    assert system_val == system_val_new, "system value changed"
    assert _flip_value(system_val) == ns_val_new, "value in namespace was not changed as expected"
