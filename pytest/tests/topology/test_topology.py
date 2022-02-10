"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2021 CESNET, z.s.p.o.

Demonstration of topology usage. To use test topologies run tests with
arguments: `--wired-loopback=<ifc>,<pci-address>`, `--vdevs` and
`--wired-spirent=<spirent-port>,<pci-address>`. For more details on
these topology arguments see tests help.
"""

from lbr_testsuite.topology.topology import select_topologies


select_topologies(['wired_loopback', 'vdev_loopback', 'wired_spirent'])

def test_topology(device, generator):
    print()
    print('Device: \n'
        f'    type: {type(device)}\n'
        f'    name: {device.get_dpdk_name()}\n'
        f'    name: {device.get_dpdk_args()}\n'
    )
    print('Generator: \n'
        f'    type: {type(generator)}\n'
    )
