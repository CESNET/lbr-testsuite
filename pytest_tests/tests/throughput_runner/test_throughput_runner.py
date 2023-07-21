"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Test the throughput_runner module.

Spirent generator sends packets to interface specified by
the '--local-interface' argument. These packets are routed
by kernel back to the spirent port. It is expected that all
packets make a full round trip back to spirent.

To run this test, it is necessary to specify the following arguments:

--local-interface
    Name of the interface where packets will be received.
--access-vlan
    Access vlan set in all incoming packets.
--spirent-chasis-port
    Spirent port used to generate traffic.
-m spirent
    Spirent test marker
"""


import itertools
import logging
from ipaddress import IPv4Interface, ip_address, ip_network
from pathlib import Path

import pytest
from pytest import fixture

from lbr_testsuite import ipconfigurer, sysctl_set_with_restore
from lbr_testsuite.spirent import STC_API_PROPRIETARY, Spirent, StreamBlock
from lbr_testsuite.throughput_runner.spirent_throughput_runner import (
    SpirentThroughputRunner,
)


DEFAULT_SPIRENT_XML_NAME = "default_config.xml"
DEFAULT_SPIRENT_XML_PATH = Path(__file__).parent.absolute() / DEFAULT_SPIRENT_XML_NAME

LOCAL_IPV4 = IPv4Interface("192.168.0.11/24")
SPIRENT_NET = ip_network("10.0.0.0/16")
GATEWAY_ADDR = ip_address("192.168.0.100")


global_logger = logging.getLogger(__name__)


@fixture
def interface_configured(local_interface):
    ip_addr = LOCAL_IPV4.ip
    ip_mask = LOCAL_IPV4.network.prefixlen

    ipconfigurer.add_ip_addr(local_interface, str(ip_addr), ip_mask)
    ipconfigurer.ifc_up(local_interface)

    yield local_interface

    ipconfigurer.ifc_down(local_interface)
    ipconfigurer.delete_ip_addr(local_interface, str(ip_addr), ip_mask)


@fixture
def routing_configured():
    configured = ipconfigurer.add_route(
        destination=str(SPIRENT_NET),
        gateway=str(GATEWAY_ADDR),
    )

    yield

    if configured:
        ipconfigurer.delete_route(
            str(SPIRENT_NET),
            str(GATEWAY_ADDR),
        )


@fixture
def forwarding_enabled(request):
    sysctl_set_with_restore(request, "net.ipv4.conf.all.forwarding", "1")


@fixture
def spirent(request):
    spirent_port = request.config.getoption("spirent_chassis_port")
    spirent_server = request.config.getoption("spirent_server")
    spirent_chassis = request.config.getoption("spirent_chassis")

    assert spirent_port is not None, "No spirent port was specified."

    instance = Spirent(
        server=spirent_server,
        chassis=spirent_chassis,
        port=spirent_port,
        api_version=STC_API_PROPRIETARY,
    )

    instance.connect()
    instance.set_config_file(DEFAULT_SPIRENT_XML_PATH)
    instance.load_config_and_connect_chassis_port()

    request.addfinalizer(instance.disconnect_chassis)
    return instance


@pytest.mark.spirent
def test_throughput_runner(
    spirent,
    interface_configured,
    routing_configured,
    forwarding_enabled,
    access_vlan,
):
    """Test that the throughput_runner module can send
    and receive traffic using spirent."""

    src_mac = spirent.determine_src_mac_address()

    sb = StreamBlock(
        spirent,
        "ipv4_192.168.0.1-10.0.0.33",
        src_mac=src_mac,
        dst_mac=ipconfigurer.ifc_status(interface_configured)["IFLA_ADDRESS"],
        vlan=access_vlan,
    )
    runner = SpirentThroughputRunner(spirent, [sb])

    # Spirent uses 100 addresses
    hosts = itertools.islice(LOCAL_IPV4.network.hosts(), 100)
    for host in hosts:
        ipconfigurer.add_ip_neigh(interface_configured, str(host), src_mac)

    runner.generate_traffic(1, 1024)
    result = runner.evaluate()
    global_logger.info(f"TX: {result[0]}, RX: {result[1]}")

    assert result[1] == result[0]
