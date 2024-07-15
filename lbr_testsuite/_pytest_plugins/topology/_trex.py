"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET

Implementation of wired trex topology. In wired trex topology
device is represented by physical port physicaly connected to a trex
generators.
"""

from collections import defaultdict

import pytest_cases

from ...topology import registration
from ...topology.device import PciDevice
from ...topology.topology import Topology
from ...trex.trex_generator import TRexMachinesPool
from ...trex.trex_manager import TRexManager
from . import _options


def _init():
    _options.add_option(
        (
            ["--wired-trex"],
            dict(
                action="append",
                default=[],
                type=str,
                help=(
                    "Add wired connection to the TRex traffic generators. "
                    "Topology consists from hostnames and PCI address of interface "
                    "connected to the TRex. Topology uses all generators available "
                    "on given hostname (see --trex-generator). Example: \n"
                    "    --wired-trex='trex;0000:01:00.0'\n"
                    "    --wired-trex='trex,trex2;0000:065:00.0'\n"
                ),
            ),
        )
    )
    _options.add_option(
        (
            ["--trex-generator"],
            dict(
                type=str,
                action="append",
                default=[],
                help=(
                    "Specify one TRex generator. "
                    "TRex generator is represented by hostname "
                    "and PCI address (separated by comma). "
                    "Examples: \n"
                    "    --trex-generator='trex,0000:b3:00.0'\n"
                    "    --trex-generator='trex2,0000:65:00.1'\n"
                ),
            ),
        )
    )
    _options.add_option(
        (
            ["--trex-force-use"],
            dict(
                default=False,
                action="store_true",
                help=(
                    "Kill any running TRex instance first. "
                    "Use this option in case you get "
                    '"TRex already taken" error.'
                ),
            ),
        )
    )

    registration.topology_option_register("wired_trex")


@pytest_cases.fixture(scope="session")
def trex_generators(request):
    """Fixture for processing --trex-generator options.

    Parameters
    ----------
    request : fixture
        Special pytest fixture used here to access
        command line arguments.

    Returns
    -------
    dict
        Dict with hostnames as keys and
        list of PCI addresses as values.
        Example:
        {
            "trex": ["0000:65:00.0", "0000:65:00.1"],
            "trex2": ["0000:65:00.0", "0000:b3:00.0"],
        }
    """

    generators = request.config.getoption("trex_generator")
    trex_machines = defaultdict(list)

    for g in generators:
        host, pci = g.split(",")
        trex_machines[host].append(pci)

    return trex_machines


@pytest_cases.fixture(scope="session")
def topology_wired_trex(devices_args, option_wired_trex, trex_generators):
    """Fixture creating TRex topology. It uses real NIC
    interface to build Device. TRex is used as a traffic
    generator.

    Note that ``generator`` fixture provided by Topology
    is not intended to be used directly. Instead,
    use ``trex_manager`` fixture.

    Parameters
    ----------
    devices_args : DevicesArgs
        Devices arguments fixture
    option_wired_trex : pseudofixture
        Dynamically defined fixture holding --wired-trex
        argument values.
    trex_generators: dict
        Parsed values from --trex-generator options.

    Returns
    -------
    Topology
        An instance of TRex Topology.
    """

    # Workaroud for a weird bug in pytest_cases similar to
    # https://github.com/smarie/python-pytest-cases/issues/37
    if option_wired_trex == pytest_cases.NOT_USED:
        return  # skip the fixture if its parameter not used

    options = option_wired_trex.split(";")

    machines = options[0].split(",")
    device_address = options[1]
    device_args = devices_args[device_address]
    topology_device = PciDevice(device_address, device_args)
    trex_machines = {k: v for k, v in trex_generators.items() if k in machines}

    topology_generator = TRexMachinesPool(trex_machines)

    return Topology(topology_device, topology_generator)


@pytest_cases.fixture(scope="module")
def trex_manager(generator):
    """Fixture providing TRex manager.

    Tests can request TRex generator(s) from TRex manager.

    Parameters
    ----------
    generator: Generator
        An instance of Topology Generator.

    Returns
    -------
    TRexManager
        TRex manager.
    """

    if isinstance(generator, TRexMachinesPool):
        return TRexManager(generator)
