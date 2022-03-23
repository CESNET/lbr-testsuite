"""
Author(s): Pavel Krobot <pavel.krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Implementation of wired loopback topology. In wired loopback topology
device and generator are represented by two physical ports
interconnected by a physical link.
"""

import pytest
import pytest_cases

from ...common.sysctl import sysctl_set_with_restore
from ...topology import registration
from ...topology.device import PciDevice
from ...topology.generator import NetdevGenerator
from ...topology.topology import Topology
from . import _options


def _init():
    _options.add_option(
        (
            ['--wired-loopback'],
            dict(
                action='append',
                default=[],
                type=str,
                help=(
                    'Add wired loopback topology of two ports, the first is a kernel interface '
                    '(its name or its PCI address) the second is PCI address. (Example: '
                    'tge3,0000:01:00.0 or 0000:04:00.0,0000:04:00.1).'
                ),
            ),
        )
    )

    registration.topology_option_register('wired_loopback')


@pytest_cases.fixture(scope='session')
def topology_wired_loopback(request, devices_args, option_wired_loopback):
    """Fixture creating wired loopback topology. Unlike vdev_loopback,
    it is uses real NIC interfaces to build Device and Generator objects
    on top of a real NIC.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture
    devices_args : DevicesArgs
        Devices arguments fixture


    Returns
    -------
    Topology
        An instance of Topology representing wired loopback
    """

    # Workaroud for a weird bug in pytest_cases similar to
    # https://github.com/smarie/python-pytest-cases/issues/37
    if option_wired_loopback == pytest_cases.NOT_USED:
        return  # skip the fixture if its parameter not used

    wlpbk = option_wired_loopback.split(",")
    if len(wlpbk) < 2:
        pytest.skip("wired loopback is missing PCI address (see --wired-loopback)")

    device_address = wlpbk[1]
    device_args = devices_args[device_address]
    device = PciDevice(device_address, device_args)
    generator = NetdevGenerator(wlpbk[0])

    sysctl_set_with_restore(request, f'net.ipv6.conf.{generator.get_netdev()}.disable_ipv6', '1')

    return Topology(device, generator)
