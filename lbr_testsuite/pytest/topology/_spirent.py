"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Implementation of wired spirent topology. In wired spirent topology
device is represented by physical port physicaly connected to a spirent
generator.
"""

import pytest_cases

from ...topology.device import PciDevice
from ...topology.topology import Topology
from ...topology import registration
from ...spirent.spirent import Spirent, STC_API_OFFICIAL, STC_API_PROPRIETARY

from . import _options


def _init():
    _options.add_option((
        ['--wired-spirent'],
        dict(
            action='append',
            default=[],
            type=str,
            help=(
                'Add wired connection to the spirent traffic generator. '
                'An argument is spirent test center chassis port followed by comma '
                'and PCI address of the interface connected to the spirent. '
                'Example: --wired-spirent=7/1,0000:01:00.0'
            )
        )
    ))
    _options.add_option((
        ['--spirent-server'],
        dict(
            type=str,
            default='termit.liberouter.org',
            help='Spirent Test Center server address'
        )
    ))
    _options.add_option((
        ['--spirent-chassis'],
        dict(
            type=str,
            default='spirent.liberouter.org',
            help='Spirent Test Center chassis address'
        )
    ))
    _options.add_option((
        ['--spirent-chassis-port'],
        dict(
            type=str,
            default='7/1',
            help='Spirent port'
        )
    ))
    _options.add_option((
        ['--spirent-api-version'],
        dict(
            type=str,
            choices=['spirent', 'liberouter'],
            default='liberouter',
            help='Spirent Test Center API version'
        )
    ))
    _options.add_option((
        ['--spirent-stc-server-port'],
        dict(
            type=int,
            default=None,
            help=(
                'Spirent Test Center server port used for communication '
                'with STC control application.'
            )
        )
    ))

    registration.topology_option_register('wired_spirent')


@pytest_cases.fixture(scope='session')
def topology_wired_spirent(request, option_wired_spirent):
    """Fixture creating spirent topology. It is uses real NIC
    interfaces to build Device and spirent as a Generator connected
    to the NIC.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture
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
        liberouter=STC_API_PROPRIETARY
    )

    # Workaroud for a weird bug in pytest_cases similar to
    # https://github.com/smarie/python-pytest-cases/issues/37
    if (option_wired_spirent == pytest_cases.NOT_USED):
        return  # skip the fixture if its parameter not used

    spirent_chassis_port, device_address = option_wired_spirent.split(",")

    device = PciDevice(device_address)

    spirent_server = request.config.getoption('spirent_server')
    spirent_chassis = request.config.getoption('spirent_chassis')
    spirent_api_version = SPIRENT_API_VERSION_CONV[request.config.getoption('spirent_api_version')]
    spirent_stc_server_port = request.config.getoption('spirent_stc_server_port')
    generator = Spirent(
            spirent_server,
            spirent_chassis,
            spirent_chassis_port,
            api_version=spirent_api_version,
            server_port=spirent_stc_server_port
    )
    generator.connect()

    return Topology(device, generator)
