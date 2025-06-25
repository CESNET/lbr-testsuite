"""
Author(s):
    Pavel Krobot <Pavel.Krobot@cesnet.cz>,

Copyright: (C) 2025 CESNET

Implementation of a topology combining two generators - netdev
generator through wired loopback and wired spirent. Device is
represented by physical port physically connected to both
generators (e.g. via a switch).
"""

import pytest
import pytest_cases

from ...common.sysctl import sysctl_set_with_restore
from ...spirent.spirent import STC_API_OFFICIAL, STC_API_PROPRIETARY, Spirent
from ...topology import registration
from ...topology.device import MultiDevice, PciDevice
from ...topology.generator import NetdevGenerator
from ...topology.topology import Topology
from . import _options


def _init():
    _options.add_option(
        (
            ["--wired-spirent-loopback"],
            dict(
                action="append",
                default=[],
                type=str,
                help=(
                    "Add wired loopback connection together with wired connection to the spirent "
                    "traffic generator. An argument is a net-dev generator kernel interface (its "
                    "name or its PCI address) followed by a comma and spirent test center chassis "
                    "port, followed by an another comma and a comma separated list of PCI "
                    "address(es) of interface(s) connected to the spirent and the kernel interface "
                    "via a switch. The first item (the kernel interface) is used for generating "
                    "of packets on loopback. To sum up, the format is: "
                    "<gen-ifc>,<port>,<dev-ifc>[,<dev-ifc2>...]"
                    "Example: \n"
                    "    --wired-spirent-loopback=tge3,7/1,0000:01:00.0\n"
                    "    --wired-spirent-loopback=0000:01:00.1,7/1,0000:01:00.0\n"
                    "    --wired-spirent-loopback=tge3,7/1,0000:01:00.0,0000:01:00.1\n"
                ),
            ),
        )
    )

    """ Note: Spirent configuration options are added within the wired-spirent
    topology in _spirent.py.
    """

    registration.topology_option_register("wired_spirent_loopback")


@pytest_cases.fixture(scope="session")
def topology_wired_spirent_loopback(request, devices_args, option_wired_spirent_loopback):
    """Fixture creating spirent-with-loopback topology. It uses real NIC
    interfaces to build Device and Generator objects on top of a real
    NIC and spirent.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture
    devices_args : DevicesArgs
        Devices arguments fixture
    option_wired_spirent_loopback : pseudofixture
        Dynamically defined fixture holding --wired-spirent-loopback
        argument values.

    Returns
    -------
    Topology
        An instance of Topology representing spirent connection.
    """

    SPIRENT_API_VERSION_CONV = dict(
        spirent=STC_API_OFFICIAL,
        liberouter=STC_API_PROPRIETARY,
    )

    # Workaroud for a weird bug in pytest_cases similar to
    # https://github.com/smarie/python-pytest-cases/issues/37
    if option_wired_spirent_loopback == pytest_cases.NOT_USED:
        return  # skip the fixture if its parameter not used

    ws_opt = option_wired_spirent_loopback.split(",")
    if len(ws_opt) < 3:
        pytest.skip(
            "missing some argument for wired spirent-with-loopback "
            "topology (see --wired-spirent-loopback)"
        )

    lpkg_gen_addr = ws_opt[0]
    spirent_chassis_port = ws_opt[1]
    devices_address = ws_opt[2:]
    assert len(devices_address) == len(set(devices_address)), "duplicate devices are not allowed"
    spirent_api_version = SPIRENT_API_VERSION_CONV[request.config.getoption("spirent_api_version")]

    loopback_generator = NetdevGenerator(lpkg_gen_addr)
    sysctl_set_with_restore(
        request,
        f"net.ipv6.conf.{loopback_generator.get_netdev()}.disable_ipv6",
        "1",
    )

    spirent_generator = Spirent(
        request.config.getoption("spirent_server"),
        request.config.getoption("spirent_chassis"),
        spirent_chassis_port,
        api_version=spirent_api_version,
        server_port=request.config.getoption("spirent_stc_server_port"),
        force_port_reservation=request.config.getoption("spirent_port_reservation_force"),
    )
    spirent_generator.connect()

    devs = []
    for addr in devices_address:
        device_args = devices_args[addr]
        d = PciDevice(addr, device_args)
        devs.append(d)

    if len(devs) == 1:
        device = devs[0]
    else:
        device = MultiDevice(devs)

    return Topology(device, (loopback_generator, spirent_generator))
