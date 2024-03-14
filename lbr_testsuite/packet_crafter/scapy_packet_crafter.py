"""
Author(s):
    Dominik Tran <tran@cesnet.cz>
    Jan Viktorin <viktorin@cesnet.cz>
    Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2022-2024 CESNET, z.s.p.o.

High-level packet crafter.
"""

import scapy.all as scapy

from . import abstract_packet_crafter, ipaddresses, ports
from .random_types import (
    RandomIPv4Header,
    RandomIPv6Header,
    RandomSCTPHeader,
    RandomTCPHeader,
    RandomUDPHeader,
)


class ScapyPacketCrafter(abstract_packet_crafter.AbstractPacketCrafter):
    """Class provides high-level packet crafting.

    Class provides methods for converting high-level packet specification
    to list of actual Scapy packets. For example, specification like::

        l2_dst='aa:bb:cc:dd:ee:ff',
        vlan_id=10,
        l3='ipv4',
        l3_src=random_types.RandomIP(44),
        l3_dst=['10.0.0.1', '12.1.1.0/28', {'first': '24.0.0.0', 'count': 8, 'step': 3}],
        l4='udp',
        l4_src=random_types.RandomPort(6),
        l4_dst=(5000,5032),
        pkt_len=1000

    will produce list of 44 * (1 + 16 + 8) * 6 * 33 = 217 800 Scapy packets. The
    packets are ready to be send (using Scapy ``sendp()`` or similar).

    For details about specification, see ``packets()`` method.
    """

    def _prepare_l3_ip(self, spec, context=None):
        """Prepare L3 scapy headers: IP(), IPv6()"""
        if spec["l3"] == "ipv4":
            IP_hdr = scapy.IP
            IPAddresses = ipaddresses.IPv4Addresses
        elif spec["l3"] == "ipv4_rand":
            IP_hdr = RandomIPv4Header()
            IPAddresses = ipaddresses.IPv4Addresses
        elif spec["l3"] == "ipv6":
            IP_hdr = scapy.IPv6
            IPAddresses = ipaddresses.IPv6Addresses
        elif spec["l3"] == "ipv6_rand":
            IP_hdr = RandomIPv6Header()
            IPAddresses = ipaddresses.IPv6Addresses
        else:
            RuntimeError(f'unsupported l3: {spec["l3"]}')

        if "l3_src" in spec:
            src = IPAddresses(spec["l3_src"])
            src = list(map(str, src.addresses_as_list()))
        else:
            src = []

        if "l3_dst" in spec:
            dst = IPAddresses(spec["l3_dst"])
            dst = list(map(str, dst.addresses_as_list()))
        else:
            dst = []

        hdrs = []

        if len(src) == 0 and len(dst) == 0:
            hdrs.append(IP_hdr())
        elif len(src) == 0:
            for dst_ip in dst:
                hdrs.append(IP_hdr(dst=dst_ip))
        elif len(dst) == 0:
            for src_ip in src:
                hdrs.append(IP_hdr(src=src_ip))
        else:
            for src_ip in src:
                for dst_ip in dst:
                    hdrs.append(IP_hdr(src=src_ip, dst=dst_ip))

        return hdrs

    def _prepare_l3_arp(self, spec, context=None):
        """Prepare L3 scapy ARP header"""
        if spec["l3"] != "arp":
            RuntimeError(f'unsupported l3: {spec["l3"]}')

        dst = (
            list(map(str, ipaddresses.IPv4Addresses(spec["l3_dst"]).addresses_as_list()))
            if "l3_dst" in spec
            else []
        )
        hdrs = []

        for dst_ip in dst:
            hdrs.append(scapy.ARP(pdst=dst_ip))

        return hdrs

    def _prepare_l4_udp_tcp_sctp(self, spec, context=None):
        """Prepare L4 scapy headers: UDP(), TCP(), SCTP()"""
        if spec["l4"] == "udp":
            L4_hdr = scapy.UDP
        elif spec["l4"] == "tcp":
            L4_hdr = scapy.TCP
        elif spec["l4"] == "sctp":
            L4_hdr = scapy.SCTP
        elif spec["l4"] == "udp_rand":
            L4_hdr = RandomUDPHeader()
        elif spec["l4"] == "tcp_rand":
            L4_hdr = RandomTCPHeader()
        elif spec["l4"] == "sctp_rand":
            L4_hdr = RandomSCTPHeader()
        else:
            RuntimeError(f'unsupported l4: {spec["l4"]}')

        hdrs = []
        src = ports.L4Ports(spec["l4_src"]).ports_as_list() if "l4_src" in spec else []
        dst = ports.L4Ports(spec["l4_dst"]).ports_as_list() if "l4_dst" in spec else []

        if len(src) == 0 and len(dst) == 0:
            hdrs.append(L4_hdr())
        elif len(src) == 0:
            for dst_port in dst:
                hdrs.append(L4_hdr(dport=dst_port))
        elif len(dst) == 0:
            for src_port in src:
                hdrs.append(L4_hdr(sport=src_port))
        else:
            for src_port in src:
                for dst_port in dst:
                    hdrs.append(L4_hdr(sport=src_port, dport=dst_port))

        return hdrs

    def _prepare_l4_ndp(self, spec, context=None):
        """Prepare L4 scapy headers: ICMPv6ND_NS()"""
        if spec["l3"] != "ipv6":
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for ndp')

        if "l3_dst" in spec:
            dst = list(map(str, ipaddresses.IPv6Addresses(spec["l3_dst"]).addresses_as_list()))
        else:
            dst = []

        return [scapy.ICMPv6ND_NS(tgt=dst_ip) for dst_ip in dst]

    def packets(self, spec):
        """Return list of scapy packets based on specification.

        Parameters
        ----------
        spec : dict
            Dict with packet specification. Following key:values are supported:

            l2_src : str, optional
                Source MAC address.
            l2_dst : str, optional
                Destination MAC address.
            vlan_id : int, optional
                VLAN ID. If not set, packet won't contain VLAN header.
            l3 : str
                Can be 'ipv4', 'ipv6', 'ipv4_rand', 'ipv6_rand' or 'arp' (for NDP see ``l4``).
                For more info on '_rand' variants see ``packet_crafter.random_types``.
            l3_src : various
                Source IP addresses. Following formats are supported:
                ``10.0.0.0``, ``2001:db8::/32``, ``{first='10.0.0.0', count=150, step=1}``,
                ``random_types.RandomIP`` or ``list`` of previous formats. For more info see
                ``packet_crafter.ipaddresses.IPv4Addresses`` and
                ``packet_crafter.ipaddresses.IPv6Addresses``.
            l3_dst : various
                Destination IP address(es). Same format as ``l3_src``.
            l4 : str
                Can be 'tcp', 'tcp_rand', 'udp', 'udp_rand', 'sctp', 'sctp_rand',
                'icmp', 'icmp_rand', 'igmp', 'igmp_rand' or 'ndp' (IPv6 only).
                For more info on '_rand' variants see ``packet_crafter.random_types``.
            l4_src : various
                Source port(s). Following formats are supported:
                10, (10-20), [10,12,17,20]. For more info see ``packet_crafter.ports.L4Ports``.
            l4_dst : int or list or tuple
                Destination port(s). Same format as ``l4_src``.
            pkt_len : int
                Packet length (without Ethernet's FCS).
            pkt_paylen : int
                Fixed number of bytes to add as payload. If ``pkt_len`` is set, then
                packet size without payload + ``pkt_paylen`` must match ``pkt_len``.

        Returns
        ------
        list(scapy.layers.l2.Ether)
            Scapy packets.
        """

        return self._prepare_pkts(spec)
