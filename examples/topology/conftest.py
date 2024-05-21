"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2024 CESNET

Implementation of example topology which requires
device, generator and analyzer.
"""

import pytest
import pytest_cases

from lbr_testsuite.topology import (
    Analyzer,
    NetdevGenerator,
    PciAddress,
    PciDevice,
    Topology,
    registration,
)
from lbr_testsuite.topology.device import MultiDevice


class CustomAnalyzer(Analyzer):
    """Custom analyzer made for example topology."""

    def __init__(self, pci: str):
        assert PciAddress.is_valid(pci), "Invalid PCI address"
        self._analyzer = pci


def pytest_addoption(parser: pytest.Parser):
    """Add example topology option."""

    parser.addoption(
        "--example-topology",
        action="append",
        default=None,
        help=(
            "Example topology. It consists from generator, device and analyzer."
            "Device can also be set as multi-device (contains multiple devices)."
            "All three components can be set as PCI address."
            "Examples:\n"
            "    --example-topology=0000:01:00.0,0000:02:00.0,0000:11:00.0\n"
            "    --example-topology=0000:01:00.0,0000:02:00.0,0000:02:00.1,0000:11:00.0\n"
        ),
    )

    registration.topology_option_register("example_topology")


@pytest_cases.fixture(scope="session")
def topology_example_topology(
    option_example_topology: str,
) -> Topology:
    """Example topology expecting device, generator and analyzer.

    Parameters
    ----------
    option_example_topology : pseudofixture
        Dynamically defined fixture holding --example-topology
        argument values.

    Returns
    -------
    Topology
        Topology with defined device, generator and analyzer.
    """

    if option_example_topology == pytest_cases.NOT_USED:
        return

    options = option_example_topology.split(",")

    if len(options) < 3:
        pytest.skip(
            "example topology requires at least 3 PCI addresses "
            "for generator, device and analyzer"
        )

    generator = NetdevGenerator(options[0])
    analyzer = CustomAnalyzer(options[-1])

    devices_address = options[1:-1]
    devs = []
    for addr in devices_address:
        devs.append(PciDevice(addr))

    if len(devs) == 1:
        device = devs[0]
    else:
        device = MultiDevice(devs)

    return Topology(device, generator, analyzer)
