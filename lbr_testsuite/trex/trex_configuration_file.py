"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Module implements creation of TRex configuration file in YAML format.
TRex requires configuration file during startup because it contains
parameters that cannot be changed during runtime - such as physical
ports of network card to be used.
"""

import random
import tempfile

import yaml

from ..common.common import compose_output_path


# Number of preallocated TRex flow objects.
# 1048576 is default value for this parameter (see
# https://trex-tgn.cisco.com/trex/doc/trex_manual.html#_memory_section_configuration)
DEFAULT_MEMORY_DP_FLOWS = 1048576

# Some configurations require higher number of preallocated flow objects.
# For example: when stateful server is overwhelmed with new connection requests,
# it needs to keep more objects in memory in order to not drop active
# or new connections.
# Increase by 16x proved to be enough for all current tests.
INCREASED_MEMORY_DP_FLOWS = 16 * DEFAULT_MEMORY_DP_FLOWS


def _setup_interfaces(interfaces, interface_count, stateful_type):
    """Interfaces must be set in pairs. This is hardwired in TRex.

    The reason for this is probably historic as TRex was originally
    designed for bidirectional communication between two interfaces. But
    sometimes you need only one interface.

    To satisfy requirement of interface pair, we can use
    special "dummy" interface. This dummy interface has no other function
    and cannot generate or receive traffic.

    For more info see https://trex-tgn.cisco.com/trex/doc/trex_manual.html#_dummy_ports.

    Currently only 4 interfaces are supported as we do not have
    any machine that has more than 4 NIC ports.
    """

    assert interface_count < 5, "Only 4 interfaces are currently supported"

    if stateful_type == "server":
        # Stateful server always uses only one physical interface.
        # Client is always on port 0, server is always on port 1 (this is hardwired in TRex).
        ifcs = ["dummy", interfaces[0]]
    else:
        if interface_count == 1:
            ifcs = [interfaces[0], "dummy"]
        elif interface_count == 2:
            ifcs = interfaces[:2]
        elif interface_count == 3:
            ifcs = interfaces[:3] + ["dummy"]
        elif interface_count == 4:
            ifcs = interfaces[:4]

    return ifcs


def _setup_cpu_cores(interface_count, cores):
    """Setup CPU cores and ``dual_if`` parameter.

    Set correct amount of CPU cores per interface pair.
    Two cores are always dedicated to 1) "master" and 2) "latency" thread.

    ``dual_if`` parameter defines list of CPU cores pinned to one interface pair.

    Currently only 4 interfaces are supported as we do not have
    any machine that has more than 4 NIC ports.

    Returns
    -------
    tuple(int, list(dict))
        First element is core count (per interface pair).
        Second element is list of CPU cores pinned to interface pairs.
    """

    assert len(cores) >= 3, "Minimum amount of CPU cores is 3"
    assert interface_count < 5, "Only 4 interfaces are currently supported"
    assert (
        len(cores) > 3 or interface_count <= 2
    ), "Combination of 3 CPU cores and 3+ interfaces is not possible"

    core_count = len(cores) - 2
    main_cores = cores[2:]

    if interface_count <= 2:
        dual_if = [{"socket": 0, "threads": main_cores}]
    else:
        core_count = core_count // 2
        dual_if = [
            {"socket": 0, "threads": main_cores[:core_count]},
            {"socket": 0, "threads": main_cores[core_count:]},
        ]

    return (core_count, dual_if)


def _setup_port_info(interface_count):
    """Setup port limit and ``port_info`` parameter.

    port_info contains destination MAC for each interface.
    We set up dummy dst MAC addresses as tests change MAC
    and VLAN dynamically during runtime.
    """

    dummy_mac = "aa:bb:aa:bb:aa:bb"

    if interface_count <= 2:
        port_limit = 2
    else:
        port_limit = 4

    port_info = [{"dest_mac": dummy_mac} for _ in range(port_limit)]

    return (port_limit, port_info)


def _save_conf_to_file(request, cfg):
    """Save YAML configuration to file and return path to this file."""

    cfg_file = str(compose_output_path(request, "trex_conf", ".yaml", tempfile.mkdtemp()))

    with open(cfg_file, "w") as f:
        yaml.dump(cfg, f)

    return cfg_file


def _create_yaml_configuration(
    generator,
    cores,
    stateful_type=None,
):
    """Create YAML configuration for TRex configuration file.

    Parameters
    ----------
    generator: TRexGenerator
        TRex generator.
    cores : list
        List of CPU cores (minimum is 3).
        If ``generator`` uses more than 2 interfaces, then it's
        recommended to use even number of cores for maximum efficiency.
    stateful_type: str, optional
        Specify whether TRex will act as a ``client`` or ``server``.
        This option is valid only if TRex is started in advanced stateful (ASTF) mode.
        Otherwise leave this parameter empty.

    Returns
    -------
    list
        YAML structure of configuration file.
    """

    assert len(cores) >= 3, "Minimum amount of CPU cores is 3"

    host = generator.get_host()
    interfaces = generator.get_interfaces()
    interface_count = len(interfaces)

    # Unique prefix is required if 2+ TRexes run on same machine.
    prefix = f"{host}-{interfaces}"

    # Remove special characters, especially space, which can cause
    # some parsing issues. For example, prefix
    # trex-['0000:65:00.0', '0000:65:00.1']
    # will be changed to
    # trex-[0000:65:00.0,0000:65:00.1]
    prefix = prefix.replace("'", "").replace(" ", "")

    memory_dp_flows = DEFAULT_MEMORY_DP_FLOWS

    if stateful_type == "server":
        memory_dp_flows = INCREASED_MEMORY_DP_FLOWS

    # Use random private port for ZMQ communication.
    # ZMQ is universal network messaging library.
    zmq_pub_port = random.randint(49152, 65534)
    zmq_rpc_port = zmq_pub_port + 1

    ifcs = _setup_interfaces(interfaces, interface_count, stateful_type)
    core_count, dual_if = _setup_cpu_cores(interface_count, cores)
    port_limit, port_info = _setup_port_info(interface_count)

    cfg = [
        {
            "port_limit": port_limit,
            "version": 2,
            "prefix": prefix,
            "zmq_pub_port": zmq_pub_port,
            "zmq_rpc_port": zmq_rpc_port,
            "interfaces": ifcs,
            "c": core_count,
            "limit_memory": 2048 * interface_count,
            "platform": {
                "master_thread_id": cores[0],
                "latency_thread_id": cores[1],
                "dual_if": dual_if,
            },
            "port_info": port_info,
            "memory": {
                "dp_flows": memory_dp_flows,
            },
        }
    ]

    return cfg


def randomize_ports(request, generator, conf_file):
    """Generate new random ZMQ ports in existing config.

    Also rewrite file on TRex server.

    Parameters
    ----------
    request : fixture
        Special pytest fixture.
    generator: TRexGenerator
        TRex generator.
    conf_file : str
        Path to configuration file on local machine.
    """

    with open(conf_file, "r") as f:
        cfg = yaml.safe_load(f)

    port = random.randint(49152, 65534)
    cfg[0]["zmq_pub_port"] = port
    cfg[0]["zmq_rpc_port"] = port + 1

    with open(conf_file, "w") as f:
        yaml.dump(cfg, f)

    daemon = generator.get_daemon()
    daemon.push_files(conf_file)


def setup_cfg_file(
    request,
    generator,
    cores,
    stateful_type=None,
):
    """Setup TRex configuration file.

    Function creates configuration file and pushes it to TRex machine.

    Parameters
    ----------
    request : fixture
        Special pytest fixture.
    generator: TRexGenerator
        TRex generator.
    first_core : int
        ID of first CPU core.
    cores : list
        List of CPU cores (minimum is 3).
        If ``generator`` uses more than 2 interfaces, then it's
        recommended to use even number of cores for maximum efficiency.
    stateful_type: str, optional
        Specify whether TRex will act as a ``client`` or ``server``.
        This option is valid only if TRex is started in advanced stateful (ASTF) mode.
        Otherwise leave this parameter empty.

    Returns
    -------
    str
        Path to configuration file on local machine.
    """

    assert len(cores) >= 3, "Minimum amount of CPU cores is 3"

    cfg = _create_yaml_configuration(generator, cores, stateful_type)
    cfg_file = _save_conf_to_file(request, cfg)

    daemon = generator.get_daemon()

    # Upload config file to TRex machine
    daemon.push_files(cfg_file)

    return cfg_file
