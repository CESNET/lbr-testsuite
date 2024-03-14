"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Unit tests of scapy_packet_crafter module.
"""

import ipaddress

import pytest
import scapy.all as scapy
import scapy.contrib.igmp as igmp

from lbr_testsuite.packet_crafter import random_types, scapy_packet_crafter

from .conftest import _is_equal


pytestmark = pytest.mark.skip("Currently not compatible with TRex Scapy used by Packet Crafter.")


def test_ipv4_udp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "udp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IP(src="10.0.0.0", dst="11.0.0.0") / scapy.UDP(sport=100, dport=200)
    ]


def test_vlan_ipv4_udp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "udp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
        / scapy.UDP(sport=100, dport=200)
    ]


def test_ipv4_tcp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "tcp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IP(src="10.0.0.0", dst="11.0.0.0") / scapy.TCP(sport=100, dport=200)
    ]


def test_vlan_ipv4_tcp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "tcp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
        / scapy.TCP(sport=100, dport=200)
    ]


def test_ipv4_sctp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "sctp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IP(src="10.0.0.0", dst="11.0.0.0") / scapy.SCTP(sport=100, dport=200)
    ]


def test_vlan_ipv4_sctp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l3_src": "10.0.0.0",
        "l3_dst": "11.0.0.0",
        "l4": "sctp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
        / scapy.SCTP(sport=100, dport=200)
    ]


def test_ipv4_icmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"l3": "ipv4", "l3_src": "10.0.0.0", "l3_dst": "11.0.0.0", "l4": "icmp"}
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IP(src="10.0.0.0", dst="11.0.0.0") / scapy.ICMP()]


def test_vlan_ipv4_icmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"vlan_id": 10, "l3": "ipv4", "l3_src": "10.0.0.0", "l3_dst": "11.0.0.0", "l4": "icmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
        / scapy.ICMP()
    ]


def test_ipv4_igmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"l3": "ipv4", "l3_src": "10.0.0.0", "l3_dst": "11.0.0.0", "l4": "igmp"}
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IP(src="10.0.0.0", dst="11.0.0.0") / igmp.IGMP()]


def test_vlan_ipv4_igmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"vlan_id": 10, "l3": "ipv4", "l3_src": "10.0.0.0", "l3_dst": "11.0.0.0", "l4": "igmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
        / igmp.IGMP()
    ]


def test_ipv4_udp_random():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l3_src": random_types.RandomIP(2, seed=333),
        "l3_dst": random_types.RandomIP(2, seed=444),
        "l4": "udp",
        "l4_src": random_types.RandomPort(2, seed=333),
        "l4_dst": random_types.RandomPort(2, seed=444),
    }

    packets = pc.packets(spec)
    assert _is_equal(
        packets,
        [
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="32.216.226.47")
            / scapy.UDP(sport=45981, dport=37724),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="32.216.226.47")
            / scapy.UDP(sport=45981, dport=40487),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="32.216.226.47")
            / scapy.UDP(sport=46286, dport=37724),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="32.216.226.47")
            / scapy.UDP(sport=46286, dport=40487),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="49.173.94.152")
            / scapy.UDP(sport=45981, dport=37724),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="49.173.94.152")
            / scapy.UDP(sport=45981, dport=40487),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="49.173.94.152")
            / scapy.UDP(sport=46286, dport=37724),
            scapy.Ether()
            / scapy.IP(src="3.105.156.39", dst="49.173.94.152")
            / scapy.UDP(sport=46286, dport=40487),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="32.216.226.47")
            / scapy.UDP(sport=45981, dport=37724),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="32.216.226.47")
            / scapy.UDP(sport=45981, dport=40487),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="32.216.226.47")
            / scapy.UDP(sport=46286, dport=37724),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="32.216.226.47")
            / scapy.UDP(sport=46286, dport=40487),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="49.173.94.152")
            / scapy.UDP(sport=45981, dport=37724),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="49.173.94.152")
            / scapy.UDP(sport=45981, dport=40487),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="49.173.94.152")
            / scapy.UDP(sport=46286, dport=37724),
            scapy.Ether()
            / scapy.IP(src="118.120.107.246", dst="49.173.94.152")
            / scapy.UDP(sport=46286, dport=40487),
        ],
    )


def test_ipv6_udp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "udp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IPv6(src="aaaa::", dst="bbbb::") / scapy.UDP(sport=100, dport=200)
    ]


def test_vlan_ipv6_udp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "udp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(src="aaaa::", dst="bbbb::")
        / scapy.UDP(sport=100, dport=200)
    ]


def test_ipv6_tcp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "tcp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IPv6(src="aaaa::", dst="bbbb::") / scapy.TCP(sport=100, dport=200)
    ]


def test_vlan_ipv6_tcp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "tcp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(src="aaaa::", dst="bbbb::")
        / scapy.TCP(sport=100, dport=200)
    ]


def test_ipv6_sctp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "sctp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IPv6(src="aaaa::", dst="bbbb::") / scapy.SCTP(sport=100, dport=200)
    ]


def test_vlan_ipv6_sctp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv6",
        "l3_src": "aaaa::",
        "l3_dst": "bbbb::",
        "l4": "sctp",
        "l4_src": 100,
        "l4_dst": 200,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(src="aaaa::", dst="bbbb::")
        / scapy.SCTP(sport=100, dport=200)
    ]


def test_ipv6_icmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"l3": "ipv6", "l3_src": "aaaa::", "l3_dst": "bbbb::", "l4": "icmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IPv6(src="aaaa::", dst="bbbb::") / scapy.ICMPv6EchoRequest()
    ]


def test_vlan_ipv6_icmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"vlan_id": 10, "l3": "ipv6", "l3_src": "aaaa::", "l3_dst": "bbbb::", "l4": "icmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(src="aaaa::", dst="bbbb::")
        / scapy.ICMPv6EchoRequest()
    ]


def test_ipv6_igmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"l3": "ipv6", "l3_src": "aaaa::", "l3_dst": "bbbb::", "l4": "igmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.IPv6(src="aaaa::", dst="bbbb::") / scapy.ICMPv6MLQuery()
    ]


def test_vlan_ipv6_igmp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {"vlan_id": 10, "l3": "ipv6", "l3_src": "aaaa::", "l3_dst": "bbbb::", "l4": "igmp"}
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(src="aaaa::", dst="bbbb::")
        / scapy.ICMPv6MLQuery()
    ]


def test_ipv6_udp_random():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l3_src": random_types.RandomIP(2, seed=333),
        "l3_dst": random_types.RandomIP(2, seed=444),
        "l4": "udp",
        "l4_src": random_types.RandomPort(2, seed=3333),
        "l4_dst": random_types.RandomPort(2, seed=4444),
    }

    packets = pc.packets(spec)
    assert _is_equal(
        packets,
        [
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=17309, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=17309, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=18793, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=18793, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=17309, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=17309, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=18793, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="373b:f221:5a67:9ea:59ce:8cfe:8e09:b24c",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=18793, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=17309, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=17309, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=18793, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4d44:dee2:dc89:f2cd:46b5:7a61:7c04:1935",
            )
            / scapy.UDP(sport=18793, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=17309, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=17309, dport=54195),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=18793, dport=35107),
            scapy.Ether()
            / scapy.IPv6(
                src="4840:ed22:1502:d9ab:6786:bf69:fba9:f210",
                dst="4f23:835c:363:88bd:49ae:3971:4f13:b86d",
            )
            / scapy.UDP(sport=18793, dport=54195),
        ],
    )


def test_arp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "arp",
        "l3_dst": "11.0.0.0",
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.ARP(pdst="11.0.0.0")]


def test_vlan_arp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "arp",
        "l3_dst": "11.0.0.0",
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.Dot1Q(vlan=10) / scapy.ARP(pdst="11.0.0.0")]


def test_ndp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l3_dst": "bbbb::",
        "l4": "ndp",
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IPv6(dst="bbbb::") / scapy.ICMPv6ND_NS(tgt="bbbb::")]


def test_vlan_ndp():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv6",
        "l3_dst": "bbbb::",
        "l4": "ndp",
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether()
        / scapy.Dot1Q(vlan=10)
        / scapy.IPv6(dst="bbbb::")
        / scapy.ICMPv6ND_NS(tgt="bbbb::")
    ]


def test_ethernet():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l2_src": "aa:bb:cc:dd:ee:ff",
        "l2_dst": "bb:cc:dd:ee:ff:aa",
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether(src="aa:bb:cc:dd:ee:ff", dst="bb:cc:dd:ee:ff:aa")]


def test_vlan_ethernet():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l2_src": "aa:bb:cc:dd:ee:ff",
        "l2_dst": "bb:cc:dd:ee:ff:aa",
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether(src="aa:bb:cc:dd:ee:ff", dst="bb:cc:dd:ee:ff:aa") / scapy.Dot1Q(vlan=10)
    ]


def test_pkt_len():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IP() / scapy.UDP() / (58 * "\x00")]


def test_vlan_pkt_len():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.Dot1Q(vlan=10) / scapy.IP() / scapy.UDP() / (54 * "\x00")
    ]


def test_pkt_paylen():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "udp",
        "pkt_paylen": 100,
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IP() / scapy.UDP() / (100 * "\x00")]


def test_vlan_pkt_paylen():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l4": "udp",
        "pkt_paylen": 100,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.Dot1Q(vlan=10) / scapy.IP() / scapy.UDP() / (100 * "\x00")
    ]


def test_pkt_len_and_paylen():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
        "pkt_paylen": 58,
    }
    packets = pc.packets(spec)
    assert packets == [scapy.Ether() / scapy.IP() / scapy.UDP() / (58 * "\x00")]


def test_vlan_test_pkt_len_and_paylen():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
        "pkt_paylen": 54,
    }
    packets = pc.packets(spec)
    assert packets == [
        scapy.Ether() / scapy.Dot1Q(vlan=10) / scapy.IP() / scapy.UDP() / (54 * "\x00")
    ]


def test_pkt_len_and_paylen_bad():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter raises error when given bad specification."""
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
        "pkt_paylen": 100,
    }
    with pytest.raises(RuntimeError):
        pc.packets(spec)


def test_vlan_test_pkt_len_and_paylen_bad():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter raises error when given bad specification."""
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "vlan_id": 10,
        "l3": "ipv4",
        "l4": "udp",
        "pkt_len": 100,
        "pkt_paylen": 100,
    }
    with pytest.raises(RuntimeError):
        pc.packets(spec)


def test_ipv4_udp_advanced():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l3_src": "10.0.0.0/31",
        "l3_dst": ["11.0.0.0", random_types.RandomIP(1, seed=123)],
        "l4": "udp",
        "l4_src": (1000, 1001),
        "l4_dst": [200, 300],
    }

    packets = pc.packets(spec)
    assert _is_equal(
        packets,
        [
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
            / scapy.UDP(sport=1000, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="11.0.0.0")
            / scapy.UDP(sport=1000, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="69.148.119.107")
            / scapy.UDP(sport=1000, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="69.148.119.107")
            / scapy.UDP(sport=1000, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
            / scapy.UDP(sport=1000, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="11.0.0.0")
            / scapy.UDP(sport=1000, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="69.148.119.107")
            / scapy.UDP(sport=1000, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="69.148.119.107")
            / scapy.UDP(sport=1000, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
            / scapy.UDP(sport=1001, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="11.0.0.0")
            / scapy.UDP(sport=1001, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="69.148.119.107")
            / scapy.UDP(sport=1001, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="69.148.119.107")
            / scapy.UDP(sport=1001, dport=200),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="11.0.0.0")
            / scapy.UDP(sport=1001, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="11.0.0.0")
            / scapy.UDP(sport=1001, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.0", dst="69.148.119.107")
            / scapy.UDP(sport=1001, dport=300),
            scapy.Ether()
            / scapy.IP(src="10.0.0.1", dst="69.148.119.107")
            / scapy.UDP(sport=1001, dport=300),
        ],
    )


def test_vlan_ipv6_tcp_advanced():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l2_dst": "bb:cc:dd:ee:ff:aa",
        "vlan_id": 10,
        "l3": "ipv6",
        "l3_src": [{"first": ipaddress.IPv6Address("aaaa::"), "count": 2, "step": 16}, "bbbb::"],
        "l3_dst": ipaddress.IPv6Address("cccc::"),
        "l4": "tcp",
        "l4_src": 300,
        "l4_dst": [400, 500],
        "pkt_paylen": 20,
    }

    packets = pc.packets(spec)
    assert _is_equal(
        packets,
        [
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="aaaa::", dst="cccc::")
            / scapy.TCP(sport=300, dport=400)
            / (20 * "\x00"),
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="aaaa::10", dst="cccc::")
            / scapy.TCP(sport=300, dport=400)
            / (20 * "\x00"),
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="bbbb::", dst="cccc::")
            / scapy.TCP(sport=300, dport=400)
            / (20 * "\x00"),
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="aaaa::", dst="cccc::")
            / scapy.TCP(sport=300, dport=500)
            / (20 * "\x00"),
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="aaaa::10", dst="cccc::")
            / scapy.TCP(sport=300, dport=500)
            / (20 * "\x00"),
            scapy.Ether(dst="bb:cc:dd:ee:ff:aa")
            / scapy.Dot1Q(vlan=10)
            / scapy.IPv6(src="bbbb::", dst="cccc::")
            / scapy.TCP(sport=300, dport=500)
            / (20 * "\x00"),
        ],
    )


def test_arp_advanced():
    """Ensure scapy_packet_crafter.ScapyPacketCrafter returns expected Scapy
    packets based on given specification.
    """
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l2_src": "aa:bb:cc:dd:ee:ff",
        "l3": "arp",
        "l3_dst": [
            {"first": ipaddress.IPv4Address("10.0.0.0"), "count": 3},
            ipaddress.IPv4Address("11.0.0.0"),
            "12.0.0.0",
            "13.0.0.0/30",
            random_types.RandomIP(2, seed=123),
        ],
        "pkt_paylen": 100,
    }

    packets = pc.packets(spec)
    assert _is_equal(
        packets,
        [
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="10.0.0.0") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="10.0.0.1") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="10.0.0.2") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="11.0.0.0") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="12.0.0.0") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="13.0.0.0") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="13.0.0.1") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="13.0.0.2") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff") / scapy.ARP(pdst="13.0.0.3") / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff")
            / scapy.ARP(pdst="69.148.119.107")
            / (100 * "\x00"),
            scapy.Ether(src="aa:bb:cc:dd:ee:ff")
            / scapy.ARP(pdst="184.135.155.222")
            / (100 * "\x00"),
        ],
    )


def test_random_ipv4():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4_rand",
    }
    ip_0 = pc.packets(spec)[0]["IP"]
    ip_1 = pc.packets(spec)[0]["IP"]

    assert ip_0.src != ip_1.src, "source addresses should be randomized"
    assert ip_0.dst != ip_1.dst, "destination addresses should be randomized"
    assert ip_0.tos != ip_1.tos, "IP TOS field should be random"
    assert ip_0.id != ip_1.id, "IP ID field should be random"
    assert ip_0.ttl != ip_1.ttl, "IP TTL field should be random"


def test_random_ipv4_fixed_addr():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4_rand",
        "l3_dst": ipaddress.ip_address("192.168.10.1"),
        "l3_src": ipaddress.ip_address("192.168.10.2"),
    }
    ip_0 = pc.packets(spec)[0]["IP"]
    ip_1 = pc.packets(spec)[0]["IP"]

    assert ip_0.src == ip_1.src, "source addresses should not be randomized"
    assert ip_0.dst == ip_1.dst, "destination addresses should not be randomized"
    assert ip_0.tos != ip_1.tos, "IP TOS field should be random"
    assert ip_0.id != ip_1.id, "IP ID field should be random"
    assert ip_0.ttl != ip_1.ttl, "IP TTL field should be random"


def test_random_ipv6():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6_rand",
    }
    ip_0 = pc.packets(spec)[0]["IPv6"]
    ip_1 = pc.packets(spec)[0]["IPv6"]

    assert ip_0.src != ip_1.src, "source addresses should be randomized"
    assert ip_0.dst != ip_1.dst, "destination addresses should be randomized"
    assert ip_0.tc != ip_1.tc, "IPv6 TC field should be random"
    assert ip_0.fl != ip_1.fl, "IPv6 FL field should be random"
    assert ip_0.hlim != ip_1.hlim, "IPv6 HopLimit field should be random"


def test_random_ipv6_fixed_addr():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6_rand",
        "l3_dst": ipaddress.ip_address("aaaa::10"),
        "l3_src": ipaddress.ip_address("bbbb::20"),
    }
    ip_0 = pc.packets(spec)[0]["IPv6"]
    ip_1 = pc.packets(spec)[0]["IPv6"]

    assert ip_0.src == ip_1.src, "source addresses should not be randomized"
    assert ip_0.dst == ip_1.dst, "destination addresses should not be randomized"
    assert ip_0.tc != ip_1.tc, "IPv6 TC field should be random"
    assert ip_0.fl != ip_1.fl, "IPv6 FL field should be random"
    assert ip_0.hlim != ip_1.hlim, "IPv6 HopLimit field should be random"


def test_random_tcp():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "tcp_rand",
    }
    ip_0 = pc.packets(spec)[0]["TCP"]
    ip_1 = pc.packets(spec)[0]["TCP"]

    assert ip_0.sport != ip_1.sport, "source port should be randomized"
    assert ip_0.dport != ip_1.dport, "destination port should be randomized"
    assert ip_0.seq != ip_1.seq, "TCP SEQ number should be random"
    assert ip_0.ack != ip_1.ack, "TCP ACK number should be random"
    assert ip_0.flags != ip_1.flags, "TCP flags should be random"
    assert ip_0.window != ip_1.window, "TCP window size should be random"
    assert ip_0.urgptr != ip_1.urgptr, "TCP urgptr field should be random"


def test_random_udp():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "udp_rand",
    }
    ip_0 = pc.packets(spec)[0]["UDP"]
    ip_1 = pc.packets(spec)[0]["UDP"]

    assert ip_0.sport != ip_1.sport, "source port should be randomized"
    assert ip_0.dport != ip_1.dport, "destination port should be randomized"


def test_random_tcp_fixed_ports():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "tcp_rand",
        "l4_src": 42,
        "l4_dst": 128,
    }
    ip_0 = pc.packets(spec)[0]["TCP"]
    ip_1 = pc.packets(spec)[0]["TCP"]

    assert ip_0.sport == ip_1.sport, "source port should not be randomized"
    assert ip_0.dport == ip_1.dport, "destination port should not be randomized"
    assert ip_0.seq != ip_1.seq, "TCP SEQ number should be random"
    assert ip_0.ack != ip_1.ack, "TCP ACK number should be random"
    assert ip_0.flags != ip_1.flags, "TCP flags should be random"
    assert ip_0.window != ip_1.window, "TCP window size should be random"
    assert ip_0.urgptr != ip_1.urgptr, "TCP urgptr field should be random"


def test_random_sctp():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "sctp_rand",
    }
    ip_0 = pc.packets(spec)[0]["SCTP"]
    ip_1 = pc.packets(spec)[0]["SCTP"]

    assert ip_0.sport != ip_1.sport, "source port should be randomized"
    assert ip_0.dport != ip_1.dport, "destination port should be randomized"
    assert ip_0.tag != ip_1.tag, "SCTP TAG should be random"


def test_random_sctp_fixed_ports():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "sctp_rand",
        "l4_src": 42,
        "l4_dst": 128,
    }
    ip_0 = pc.packets(spec)[0]["SCTP"]
    ip_1 = pc.packets(spec)[0]["SCTP"]

    assert ip_0.sport == ip_1.sport, "source port should not be randomized"
    assert ip_0.dport == ip_1.dport, "destination port should not be randomized"
    assert ip_0.tag != ip_1.tag, "SCTP TAG should be random"


def test_random_icmp():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "icmp_rand",
    }
    ip_0 = pc.packets(spec)[0]["ICMP"]
    ip_1 = pc.packets(spec)[0]["ICMP"]

    assert ip_0.code != ip_1.code, "ICMP code should be random"


def test_random_icmpv6():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l4": "icmp_rand",
    }
    ip_0 = pc.packets(spec)[0]["ICMPv6EchoRequest"]
    ip_1 = pc.packets(spec)[0]["ICMPv6EchoRequest"]

    assert ip_0.code != ip_1.code, "ICMPv6 code should be random"
    assert ip_0.id != ip_1.id, "ICMPv6 ID should be random"
    assert ip_0.seq != ip_1.seq, "ICMPv6 sequence number should be random"


def test_random_igmp():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv4",
        "l4": "igmp_rand",
    }
    ip_0 = pc.packets(spec)[0]["IGMP"]
    ip_1 = pc.packets(spec)[0]["IGMP"]

    assert ip_0.mrcode != ip_1.mrcode, "IGMP mrcode should be random"
    assert ip_0.gaddr != ip_1.gaddr, "ICMPv6 gaddr should be random"


def test_random_mld():
    pc = scapy_packet_crafter.ScapyPacketCrafter()
    spec = {
        "l3": "ipv6",
        "l4": "igmp_rand",
    }
    ip_0 = pc.packets(spec)[0]["ICMPv6MLQuery"]
    ip_1 = pc.packets(spec)[0]["ICMPv6MLQuery"]

    assert ip_0.code != ip_1.code, "MLD code should be random"
    assert ip_0.mrd != ip_1.mrd, "MLD MRD field should be random"
    assert ip_0.mladdr != ip_1.mladdr, "MLD mladdr field should be random"
