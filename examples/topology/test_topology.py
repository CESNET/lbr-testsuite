"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2021 CESNET, z.s.p.o.

Demonstration of topology usage. To use test topologies run tests with
arguments: `--wired-loopback=<ifc>,<pci-address>`, `--vdevs` and
`--wired-spirent=<spirent-port>,<pci-address>`. For more details on
these topology arguments see tests help.
"""

from lbr_testsuite.topology.device import MultiDevice
from lbr_testsuite.topology.topology import select_topologies


select_topologies(["wired_loopback", "vdev_loopback", "wired_spirent", "example_topology"])


def _print_device(device):
    print(f"    type: {type(device)}")
    print(f"    name: {device.get_dpdk_name()}")
    print(f"    args: {device.get_dpdk_args()}")


def test_topology(device, generator, analyzer):
    print()
    print("Device:")

    if isinstance(device, MultiDevice):
        for dev in device.get_base_devices():
            _print_device(dev)
    else:
        _print_device(device)

    print("Generator:")
    print(f"    type: {type(generator)}")
    print("Analyzer:")
    print(f"    type: {type(analyzer)}")
