"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2022 CESNET

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
    _dpdk_devargs : dict[str]
        Dictionary of DPDK device arguments.
    _dpdk_name : str
        Name of the device in DPDK runtime.
    """

    def __init__(self):
        """Device constructor expects to be extended."""

        self._dpdk_args = []
        self._dpdk_devargs = {}
        self._dpdk_name = None

    def _dpdk_device(self):
        """Returns DPDK device specification for command-line.

        Returns
        -------
        str
            Device specification.
        """

        return None

    def get_dpdk_args(self):
        """Gets list of DPDK EAL (Environment Abstraction Layer)
        parameters needed.

        Returns
        -------
        list[str]
            List of DPDK EAL parameters.
        """

        device = self._dpdk_device()
        if not device:
            return self._dpdk_args

        for key, val in self._dpdk_devargs.items():
            device = device + f",{key}={val}"

        return [device] + self._dpdk_args

    def get_dpdk_devargs(self):
        """Gets dictionary of DPDK device arguments.

        Returns
        -------
        dict[str]
            Dictionary of DPDK device arguments.
        """

        return self._dpdk_devargs

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
    _address : pci_address.PciAddress
        PCIe device address.
    """

    def _dpdk_device(self):
        return f"--allow={self._address}"

    def __init__(self, address, devargs=None):
        """The device object based on a real PCIe device.

        Parameters
        ----------
        address : str
            address of PCIe device
        devargs : dict[str], optional
            device arguments

        Raises
        ------
        RuntimeError
            If no such PCIe device.
        """

        super().__init__()

        if not isdir(f"/sys/bus/pci/devices/{address}"):
            raise RuntimeError(f"no such PCIe device '{address}'")

        self._address = PciAddress.from_string(address)
        self._dpdk_name = str(address)
        if devargs:
            self._dpdk_devargs = devargs

    def get_address(self):
        """Gets PCIe address of the device.

        Returns
        -------
        pci_address.PciAddress
            PCIe address.
        """

        return self._address


class VdevDevice(Device):
    """Derived class representing a virtual device."""

    def _dpdk_device(self):
        return f"--vdev={self._dpdk_name}"

    def __init__(self):
        """The DPDK virtual device object."""

        super().__init__()
        self._dpdk_args.extend(["--no-pci"])


class RingDevice(VdevDevice):
    """Derived class representing a ring device."""

    def __init__(self, id=0):
        """The DPDK ring device object.

        Parameters
        ----------
        id : int, optional
            ring virtual device identification
        """

        super().__init__()
        self._dpdk_name = f"net_ring{id}"


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

        if not isdir(f"/sys/class/net/{netdev}"):
            raise RuntimeError(f"no such network interface '{netdev}'")

        self._netdev = str(netdev)
        self._dpdk_devargs["iface"] = self._netdev
        self._dpdk_name = f"net_pcap{id}"


class MultiDevice(Device):
    """Derived class representing a compound device.

    Attributes
    ----------
    _devices : list[Devices]
        List of base devices.
    """

    def __init__(self, devices):
        """The MultiDevice object based on a list of base devices.

        Parameters
        ----------
        device : list[Devices]
            list of base Device instances

        Raises
        ------
        RuntimeError
            If the list is empty.
        """

        super().__init__()

        if len(devices) == 0:
            raise RuntimeError(f"devices list empty")

        self._devices = devices

    def get_dpdk_args(self):
        """Gets list of DPDK EAL (Environment Abstraction Layer)
        parameters needed.

        Returns
        -------
        list[str]
            List of DPDK EAL parameters.
        """

        dpdk_args = []

        for device in self._devices:
            dpdk_args = dpdk_args + device.get_dpdk_args()

        return dpdk_args

    def get_base_devices(self):
        """Gets list of base devices.

        Returns
        -------
        list[Devices]
            Base devices.
        """

        return self._devices

    def _unsupported_method_called(self):
        assert False, "invalid method call for MultiDevice"

    def get_dpdk_devargs(self):
        """Calling this method on MultiDevice makes no sense. Device
        arguments has to be handled for individual devices.
        """

        self._unsupported_method_called()

    def get_dpdk_name(self):
        """Calling this method on MultiDevice makes no sense. Device
        name has to be retrieved for individual devices.
        """

        self._unsupported_method_called()
