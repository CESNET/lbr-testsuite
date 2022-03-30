"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2022 CESNET

Traffic generator classes. All the specific traffic generator classes
should extend base Generator class.
"""

import errno
from os import listdir
from os.path import isdir

from ..ipconfigurer import ipconfigurer
from .pci_address import PciAddress


class Generator:
    """Base generator class. The class from
    which other traffic generators are derived.
    """

    def wait_until_ready(self):
        """Wait for the generator to be ready."""

        pass


class NetdevGenerator(Generator):
    """Net device traffic generator class.

    Attributes
    ----------
    _netdev : str
        Net device interface name.
    _carrier_timeout: int
        Maximal time in seconds to wait for interface carrier.
    """

    def _convert_pci_to_netdev(self, address):
        """Converts the PCIe device address to a network interface name.

        Parameters
        ----------
        address : str
            address of PCIe device

        Raises
        ------
        OSError
            If no such PCIe device or no related network interfaces found.

        Returns
        -------
        str
            Interface name.
        """

        if not isdir(f"/sys/bus/pci/devices/{address}"):
            raise OSError(errno.ENODEV, f"no such PCIe device '{address}'")

        netdevs = [f for f in listdir(f"/sys/bus/pci/devices/{address}/net")]
        if len(netdevs) <= 0:
            raise OSError(errno.ENOENT, f"no network interface related to '{address}' found")

        assert len(netdevs) <= 1, "there should be only one netdev per PCIe address"

        return netdevs[0]

    def __init__(self, netdev):
        """The traffic generator based on the kernel network interface.

        Parameters
        ----------
        netdev : str
            net device interface name or PCI device address

        Raises
        ------
        OSError
            If no such network interface.
        """

        if PciAddress.is_valid(netdev):
            netdev = self._convert_pci_to_netdev(netdev)

        if not isdir(f"/sys/class/net/{netdev}"):
            raise OSError(errno.ENODEV, f"no such network interface '{netdev}'")

        self._netdev = str(netdev)
        self._carrier_timeout = 4

    def get_netdev(self):
        """Gets the original net device interface name.

        Returns
        -------
        str
            Interface name.
        """

        return self._netdev

    def wait_until_ready(self):
        """Wait for the generator to be ready. It effectively
        waits for carrier on the underlying net device to be up.
        """

        ipconfigurer.wait_until_ifc_carrier(self.get_netdev(), timeout=self._carrier_timeout)
