"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET

Module for configuring the Network Interface Card.
"""

import logging
from pathlib import Path

from lbr_testsuite import executable
from lbr_testsuite.topology.device import Device, MultiDevice


global_logger = logging.getLogger(__name__)


class SetpciError(RuntimeError):
    """Exception raised for `setpci` failures."""

    def __init__(self, msg: str):
        self.msg = f"Setpci command unexpected outpu: {msg}"
        super().__init__(self.msg)


def get_interfaces_by_device(device: Device) -> list:
    """Obtain system interface names based on the provided devices'
    PCI address. If the device object represents a single PCI device,
    a single-element list is returned, otherwise the output contains
    names of all sub-devices.

    Parameters
    ----------
    device : Device
        Device to lookup interface name.

    Returns
    -------
    list(str)
        List of interface names corresponding to the device.
    """

    base_path = Path("/sys/bus/pci/devices/")

    if isinstance(device, MultiDevice):
        dev_addrs = [str(dev.get_address()) for dev in device.get_base_devices()]
    else:
        dev_addrs = [str(device.get_address())]

    ifname_paths = [Path(base_path / dev_addr / "net").glob("*") for dev_addr in dev_addrs]
    ifnames = [next(ifname_list).name for ifname_list in ifname_paths]

    return ifnames


def _ethtool_get_flow_control(ifname: str) -> dict:
    stdout, _ = executable.Tool(["ethtool", "-a", ifname]).run()

    # The format is as follows:
    #   ```
    #   Pause parameters for ens1f0np0:
    #   Autonegotiate:  off
    #   RX:             off
    #   TX:             off
    #   ````

    fc_status = stdout.splitlines()[1:]
    fc_status_dict = {}

    for line in fc_status:
        if line.strip() == "":
            continue

        props = line.split(":")
        key = props[0].strip()
        val = props[1].strip()
        fc_status_dict[key] = val

    return fc_status_dict


def ethtool_set_flow_control(ifname: str, rx: str, tx: str):
    """Set flow control parameters of ifname using ethtool.

    Disabling flow control should increase DPDK application
    throughput significantly (rx="off", tx="off").

    Taken from MLX5 performance report:
    https://fast.dpdk.org/doc/perf/DPDK_22_07_NVIDIA_Mellanox_NIC_performance_report.pdf

    Parameters
    ----------
    ifname : str
        Interface name.
    rx : str
        RX flow control desired setting ('on' or 'off').
    tx : str
        TX flow control desired setting ('on' or 'off').
    """

    fc_status = _ethtool_get_flow_control(ifname)
    fc_args = []

    if fc_status["RX"] != rx:
        fc_args.extend(["rx", rx])

    if fc_status["TX"] != tx:
        fc_args.extend(["tx", tx])

    if len(fc_args) == 0:
        # If the current status is already set to the desired
        # value, skip the ethtool command entirely as it would
        # end with a non-zero exit code when performing an
        # empty operation.
        global_logger.debug("flow control already set, skipping configuration")
        return

    cmd_args = ["ethtool", "-A", ifname] + fc_args

    executable.Tool(cmd_args, sudo=True).run()


def get_device_addresses(device: Device) -> list:
    """Obtain PCI addresses for given device. If the device is a single device,
    the output list will contain a single element, otherwise there is an address
    for each device within MultiDevice

    Parameters
    ----------
    device : Device
        Device to read PCI address from.

    Returns
    -------
    list(str)
        List of PCI addresses corresponding to given device.
    """

    if isinstance(device, MultiDevice):
        pci_addrs = [str(dev.get_address()) for dev in device.get_base_devices()]
    else:
        pci_addrs = [str(device.get_address())]

    return pci_addrs


def optimize_mlx5_pci_request(device: Device):
    """Optimize the PCI read request size to 1024 bytes to increase
    the throughput of DPDK applications running with MLX5 NICs.

    Taken from MLX5 performance report:
    https://fast.dpdk.org/doc/perf/DPDK_22_07_NVIDIA_Mellanox_NIC_performance_report.pdf

    Parameters
    ----------
    device : Device
        An instance of bound Device.
    """

    def read_reg(pci_addr):
        stdout, stderr = executable.Tool(["setpci", "-s", pci_addr, "68.w"], sudo=True).run()

        return stdout.strip(), stderr

    def write_reg(pci_addr, val):
        executable.Tool(["setpci", "-s", pci_addr, f"68.w={val}"], sudo=True).run()

    for addr in get_device_addresses(device):
        # Read the MaxReadReq register.
        orig_reg, _ = read_reg(addr)
        if len(orig_reg) != 4:
            raise SetpciError(f"expected 4 characters, got {orig_reg}")

        # Replace first byte with 3.
        new_reg = f"3{orig_reg[1:]}"
        # Write the MaxReadReq register.
        write_reg(addr, new_reg)

        # Check the MaxReadReq register was updated
        check_reg, _ = read_reg(addr)
        if check_reg != new_reg:
            raise SetpciError(f"register was not updated, expected {check_reg}, got {new_reg}")
