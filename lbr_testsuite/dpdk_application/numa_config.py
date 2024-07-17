"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

NUMA configuration inspector.
"""

from pathlib import Path


class NUMAConfig:
    """Helper class used to acquire the current system's
    configuration of NUMA nodes and the attached CPUs or devices.
    """

    NUMA_SYS_PATH = Path("/sys/devices/system/node/")
    PCI_DEV_PATH = Path("/sys/bus/pci/devices/")

    def __init__(self):
        pass

    def cpu_mapping(self) -> dict:
        """Access the current machine's NUMA node to CPU cores
        mapping.

        Returns
        -------
        dict
            Dictionary with NUMA nodes as keys and lists of CPU cores
            as values. Example:
            {
                "node0": [0, 2, 4, 6, 8, 10],
                "node1": [1, 3, 5, 7, 9, 11],
            }
        """

        nodes = self.NUMA_SYS_PATH.glob("node*")
        config = dict()

        for node in nodes:
            cpulist = self._cpulist(node / "cpulist")
            config[node.name] = cpulist

        return config

    def device_cpus(self, pci_addr: str) -> list:
        """Obtain CPU cores that are local to the provided PCI
        device (in the same NUMA node)

        Parameters
        ----------
        pci_addr : str
            Device's PCI address. Expected format: 'ABCD:EF:GH.I'.

        Returns
        -------
        list
            List of CPUs that are local to the PCI device.
        """

        return self._cpulist(self.PCI_DEV_PATH / pci_addr / "local_cpulist")

    def _cpulist_single(self, range_str: str) -> list:
        """Convert a single CPU definition"""

        cpu_range = list(map(int, range_str.split("-", maxsplit=2)))

        if len(cpu_range) == 2:
            return list(range(cpu_range[0], cpu_range[1] + 1))
        else:
            return cpu_range

    def _cpulist(self, list_path: Path) -> list:
        with open(list_path, "r") as f:
            cpulist_str = f.read()

        cpulist = []

        cpu_defs = cpulist_str.split(",")
        for cpu_def in cpu_defs:
            cpulist.extend(self._cpulist_single(cpu_def))

        return cpulist
