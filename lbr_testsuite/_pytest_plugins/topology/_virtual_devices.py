"""
Author(s): Pavel Krobot <pavel.krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Implementation of virtual devices topologies (vdev loopback and vdev
ring).
"""

import pytest_cases

from ...common.sysctl import sysctl_set
from ...ipconfigurer import ipconfigurer as ipconf
from ...topology import registration
from ...topology.device import PcapLiveDevice, RingDevice
from ...topology.generator import NetdevGenerator
from ...topology.topology import Topology
from . import _options


def _init():
    _options.add_option(
        (
            ["--vdevs"],
            dict(
                action="store_true",
                default=None,
                help=(
                    "Enable virtual topologies, e.g., vdev_loopback and vdev_ring. This collects "
                    "also tests that supports these virtual topologies. By default virtual "
                    "topologies are disabled."
                ),
            ),
        )
    )

    registration.topology_option_register("vdevs")


@pytest_cases.fixture(scope="session")
def topology_vdev_loopback(request, require_root, option_vdevs):
    """Fixture creating virtual loopback topology. Internally, it adds
    veth network interfaces pair (testing-vdev0p0 and testing-vdev0p1).
    The first interface is used to build the Device object, the second
    is used to build the Generator object.
    """

    vethpeers = ("testing-vdev0p0", "testing-vdev0p1")

    ipconf.add_link(vethpeers[0], kind="veth", peer=vethpeers[1])
    request.addfinalizer(lambda: ipconf.delete_link(vethpeers[0]))

    ipconf.ifc_up(vethpeers[0])
    request.addfinalizer(lambda: ipconf.ifc_down(vethpeers[0]))

    sysctl_set(f"net.ipv6.conf.{vethpeers[0]}.disable_ipv6", "1")
    sysctl_set(f"net.ipv6.conf.{vethpeers[1]}.disable_ipv6", "1")

    device = PcapLiveDevice(vethpeers[0])
    generator = NetdevGenerator(vethpeers[1])

    return Topology(device, generator)


@pytest_cases.fixture(scope="session")
def topology_vdev_ring(option_vdevs):
    """Fixture creating virtual ring topology. Internally, the topology
    is build only on top of RingDevice object without any traffic
    generator (Generator object). Packets transmitted on the device are
    received again.
    """

    device = RingDevice()
    return Topology(device)
