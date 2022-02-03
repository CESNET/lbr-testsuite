"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2021 CESNET

Device classes.
"""

from os.path import isdir

from .pci_address import PciAddress


class Device:
    """Base device class. The class from
    which other devices are derived.

    Attributes
    ----------
    _dpdk_args : list[str]
        List of DPDK EAL (Environment Abstraction Layer) parameters.
    _dpdk_name : str
        Name of the device in DPDK runtime.
    """

    def __init__(self):
        """Device constructor expects to be extended.
        """

        self._dpdk_args = []
        self._dpdk_name = None

    def get_dpdk_args(self):
        """Gets list of DPDK EAL (Environment Abstraction Layer)
        parameters needed.

        Returns
        -------
        list[str]
            List of DPDK EAL parameters.
        """

        return self._dpdk_args

    def get_dpdk_name(self):
        """Gets name of the device in DPDK runtime.

        Returns
        -------
        str: Name of the device.
        """

        return self._dpdk_name


class PciDevice(Device):
    """Derived class representing a PCIe device.

    Attributes
    ----------
    _address : PciAddress
        PCIe device address.
    """

    def __init__(self, address):
        """The device object based on a real PCIe device.

        Parameters
        ----------
        address : str
            address of PCIe device

        Raises
        ------
        RuntimeError
            If no such PCIe device.
        """

        super().__init__()

        if not isdir(f'/sys/bus/pci/devices/{address}'):
            raise RuntimeError(f"no such PCIe device '{address}'")

        self._address = PciAddress.from_string(address)
        self._dpdk_args.extend([f'--allow={self._address}'])
        self._dpdk_name = str(address)

    def get_address(self):
        """Gets PCIe address of the device.

        Returns
        -------
        PciAddress
            PCIe address.
        """

        return self._address


class VdevDevice(Device):
    """Derived class representing a virtual device.
    """

    def __init__(self):
        """The DPDK virtual device object.
        """

        super().__init__()
        self._dpdk_args.extend(['--no-pci'])


class RingDevice(VdevDevice):
    """Derived class representing a ring device.
    """

    def __init__(self, id=0):
        """The DPDK ring device object.

        Parameters
        ----------
        id : int, optional
            ring virtual device identification
        """

        super().__init__()
        self._dpdk_args.extend(['--vdev=net_ring0'])
        self._dpdk_name = f'net_ring{id}'


class PcapLiveDevice(VdevDevice):
    """Derived class representing a live PCAP device.

    Attributes
    ----------
    _netdev : str
        Net device interface name.
    """

    def __init__(self, netdev, id=0):
        """The PCAP device object based on a kernel network interface.

        Parameters
        ----------
        netdev : str
            net device interface name
        id : int, optional
            pcap virtual device identification

        Raises
        ------
        RuntimeError
            If no such network interface.
        """

        super().__init__()

        if not isdir(f'/sys/class/net/{netdev}'):
            raise RuntimeError(f"no such network interface '{netdev}'")

        self._netdev = str(netdev)
        self._dpdk_args.extend([f'--vdev=net_pcap0,iface={self._netdev}'])
        self._dpdk_name = f'net_pcap{id}'