"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Module for composing DPDK lcore arguments.
"""

from itertools import islice
from typing import Dict, List, Tuple

from lbr_testsuite.dpdk_application.numa_config import NUMAConfig
from lbr_testsuite.topology.device import Device, MultiDevice, PciDevice, VdevDevice


def _determine_vdev_lcores(pipeline_workers: int, extra_workers: int) -> Tuple[int, List[int]]:
    """Determine DPDK lcores used by a DPDK application using a virtual device
    (vdev). This function is NUMA-aware and all returned lcores are situated
    within the same NUMA node.

    Parameters
    ----------
    pipeline_workers : int
        Number of requested workers. Not including the main lcore.
    extra_workers : int
        Number of workers outside the main pipeline. Not including the main lcore.

    Returns
    -------
    Tuple[int, List[int]]
        Tuple containing the main lcore and a list of worker lcores.
    """

    numa = NUMAConfig().cpu_mapping()
    node, cpulist = next(iter(numa.items()))

    main_lcore = cpulist[0]
    worker_lcore_cnt = pipeline_workers + extra_workers + 1
    worker_lcores = cpulist[:worker_lcore_cnt]

    return main_lcore, worker_lcores


def _determine_num_lcores_per_dev(
    pipeline_workers: int,
    extra_workers: int,
    devs: List[str],
) -> Dict[str, int]:
    """Determine the number of lcore workers per each device. In case the
    total number of workers cannot be equally balanced, some devices may
    receive one extra worker.
    """

    total_workers = pipeline_workers + extra_workers
    workers_per_dev = total_workers // len(devs)
    rem_workers = total_workers % len(devs)

    dev_map = {dev: workers_per_dev for dev in devs}
    for dev in dev_map:
        if rem_workers > 0:
            dev_map[dev] += 1
            rem_workers -= 1
        else:
            break

    return dev_map


def _determine_devices_lcores(
    pipeline_workers: int,
    extra_workers: int,
    devs: List[PciDevice],
) -> Tuple[int, List[int]]:
    """Determine DPDK lcores used a by a DPDK application using PCI
    devices. This function is NUMA-aware and the returned lcores are
    distributed among different NUMA nodes based on the provided devices
    list.

    Parameters
    ----------
    pipeline_workers : int
        Number of requested workers. Not including the main lcore.
    extra_workers : int
        Number of extra workers outside the main pipeline
        (i.e. protector's system interface worker). Not including the main lcore.
    devs : List[PciDevice]
        List of devices required to assess NUMA distribution.

    Returns
    -------
    Tuple[int, List[int]]
        Tuple containing the main lcore and a list of worker lcores.
    """

    dev_addrs = [str(dev.get_address()) for dev in devs]

    numa = NUMAConfig()
    main_lcore = numa.device_cpus(dev_addrs[0])[0]
    used_lcores = {main_lcore}

    lcore_cnt_per_dev = _determine_num_lcores_per_dev(
        pipeline_workers,
        extra_workers,
        dev_addrs,
    )

    for da in dev_addrs:
        dev_cpus = set(numa.device_cpus(da))
        dev_cpu_cnt = lcore_cnt_per_dev[da]

        available_cpus = dev_cpus - used_lcores
        selected_cpus = set(islice(available_cpus, dev_cpu_cnt))
        used_lcores |= selected_cpus

    return main_lcore, list(used_lcores)


def determine_lcores(
    pipeline_workers: int,
    extra_workers: int,
    dev: Device,
) -> Tuple[int, List[int]]:
    """Determine DPDK lcores used a by a DPDK application.
    This function is NUMA-aware and the returned lcores are distributed
    among different NUMA nodes based on the provided device.

    Parameters
    ----------
    workers_count : int
        Number of requested workers. Not including the main lcore.
    extra_workers : int
        Number of extra workers outside the main pipeline
        (i.e. protector's system interface worker). Not including the main lcore.
    dev : Device
        Device used to asses NUMA configuration

    Returns
    -------
    Tuple[int, List[int]]
        Tuple containing the main lcore and a list of worker lcores.
    """

    if isinstance(dev, VdevDevice):
        return _determine_vdev_lcores(pipeline_workers, extra_workers)
    elif isinstance(dev, MultiDevice):
        return _determine_devices_lcores(pipeline_workers, extra_workers, dev.get_base_devices())
    else:
        return _determine_devices_lcores(pipeline_workers, extra_workers, [dev])


def _compose_lcore_args(lcore_config: Tuple[int, List[int]]) -> List[str]:
    """Compose DPDK arguments corresponding to the provided lcore configuration.

    Parameters
    ----------
    lcore_config : Tuple[int, List[int]]
        Configuration of lcores in the format (main_lcore, [other_lcores]).

    Returns
    -------
    List[str]
        List of strings representing the individual command-line arguments
        passed to the DPDK application.
    """

    main_lcore_args = f"--main-lcore={str(lcore_config[0])}"
    worker_lcores_str = ",".join(map(str, lcore_config[1]))
    worker_lcores_args = f"-l {worker_lcores_str}"

    return [main_lcore_args, worker_lcores_args]


def device_lcore_args(pipeline_workers: int, extra_workers: int, dev: Device) -> List[str]:
    """Determine DPDK args to ensure the appropriate lcores are allocated
    according to the provided device. This function distributes lcores
    in a NUMA-aware way, therefore the lcores belong to the device's NUMA
    node (or multiple in case of MultiDevice).

    Note that a main lcore configuration is also determined by this function.

    Parameters
    ----------
    workers_count : int
        Number of worker lcores (not including the main lcore).
    extra_workers : int
        Number of extra workers outside the main pipeline
        (i.e. protector's system interface worker). Not including the main lcore.
    dev : Device
        Device used to assess NUMA configuration.

    Returns
    -------
    List[str]
        List representing the individual command-line arguments
        passed to the DPDK application.
    """

    lcore_config = determine_lcores(pipeline_workers, extra_workers, dev)
    return _compose_lcore_args(lcore_config)
