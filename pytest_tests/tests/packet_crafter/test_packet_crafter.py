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
