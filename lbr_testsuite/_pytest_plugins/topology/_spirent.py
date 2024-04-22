"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Implementation of wired spirent topology. In wired spirent topology
device is represented by physical port physicaly connected to a spirent
generator.
"""

import pytest
import pytest_cases

from ...spirent.spirent import STC_API_OFFICIAL, STC_API_PROPRIETARY, Spirent
from ...topology import registration
from ...topology.device import MultiDevice, PciDevice
from ...topology.topology import Topology
from . import _options


def _init():
    _options.add_option(
        (
            ["--wired-spirent"],
            dict(
                action="append",
                default=[],
                type=str,
                help=(
                    "Add wired connection to the spirent traffic generator. "
                    "An argument is spirent test center chassis port followed by comma "
                    "and comma separated list of PCI address(es) of the interface(s) "
                    "connected to the spirent. "
                    "Example: \n"
                    "    --wired-spirent=7/1,0000:01:00.0\n"
                    "    --wired-spirent=7/1,0000:01:00.0,0000:01:00.1\n"
                ),
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-server"],
            dict(
                type=str,
                default="termit.liberouter.org",
                help="Spirent Test Center server address",
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-chassis"],
            dict(
                type=str,
                default="spirent.liberouter.org",
                help="Spirent Test Center chassis address",
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-chassis-port"],
            dict(
                type=str,
                default="",
                help="Spirent port",
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-api-version"],
            dict(
                type=str,
                choices=["spirent", "liberouter"],
                default="liberouter",
                help="Spirent Test Center API version",
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-stc-server-port"],
            dict(
                type=int,
                default=None,
                help=(
                    "Spirent Test Center server port used for communication "
                    "with STC control application."
                ),
            ),
        )
    )
    _options.add_option(
        (
            ["--spirent-port-reservation-force"],
            dict(
                default=False,
                action="store_true",
                help=(
                    "Force reservation of spirent chassis port. Use with caution as this "
                    "terminates any current reservation."
                ),
            ),
        )
    )

    registration.topology_option_register("wired_spirent")


@pytest_cases.fixture(scope="session")
def topology_wired_spirent(request, devices_args, option_wired_spirent):
    """Fixture creating spirent topology. It is uses real NIC
    interfaces to build Device and spirent as a Generator connected
    to the NIC.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture
    devices_args : DevicesArgs
        Devices arguments fixture
    option_wired_spirent : pseudofixture
        Dynamically defined fixture holding --wired-spirent
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
    if option_wired_spirent == pytest_cases.NOT_USED:
        return  # skip the fixture if its parameter not used

    ws_opt = option_wired_spirent.split(",")
    if len(ws_opt) < 2:
        pytest.skip("missing some argument for wired spirent topology (see --wired-spirent)")

    spirent_chassis_port = ws_opt[0]
    devices_address = ws_opt[1:]
    assert len(devices_address) == len(set(devices_address)), "duplicate devices are not allowed"
    spirent_api_version = SPIRENT_API_VERSION_CONV[request.config.getoption("spirent_api_version")]

    devs = []
    for addr in devices_address:
        device_args = devices_args[addr]
        d = PciDevice(addr, device_args)
        devs.append(d)

    if len(devs) == 1:
        device = devs[0]
    else:
        device = MultiDevice(devs)

    generator = Spirent(
        request.config.getoption("spirent_server"),
        request.config.getoption("spirent_chassis"),
        spirent_chassis_port,
        api_version=spirent_api_version,
        server_port=request.config.getoption("spirent_stc_server_port"),
        force_port_reservation=request.config.getoption("spirent_port_reservation_force"),
    )
    generator.connect()

    return Topology(device, generator)
