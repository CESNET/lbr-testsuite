"""
Author(s):
    Dominik Tran <tran@cesnet.cz>
    Jan Viktorin <viktorin@cesnet.cz>
    Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2022-2024 CESNET, z.s.p.o.

Abstract packet crafter.
"""

import abc

import scapy.all as scapy
import scapy.contrib.igmp as igmp

from .random_types import (
    RandomICMPHeader,
    RandomICMPv6Header,
    RandomIGMPHeader,
    RandomMLDHeader,
)


class AbstractPacketCrafter(abc.ABC):
    """Class provides common code for packet crafters.

    See derived classes for usage example.
    """

    def _prepare_l2(self, spec, context=None):
        """Prepare L2 scapy headers: Ether(), Dot1Q()"""
        kwargs = {}

        if "l2_src" in spec:
            kwargs["src"] = spec["l2_src"]
        if "l2_dst" in spec:
            kwargs["dst"] = spec["l2_dst"]

        if "vlan_id" in spec:
            return [scapy.Ether(**kwargs) / scapy.Dot1Q(vlan=spec["vlan_id"])]
        else:
            return [scapy.Ether(**kwargs)]

    @abc.abstractmethod
    def _prepare_l3_ip(self, spec, context=None):
        """Prepare L3 scapy headers: IP(), IPv6()"""
        ...

    @abc.abstractmethod
    def _prepare_l3_arp(self, spec, context=None):
        """Prepare L3 scapy ARP header"""
        ...

    def _prepare_l3(self, spec, context=None):
        """Prepare L3 scapy headers."""
        if "l3" not in spec:
            return []

        if spec["l3"] in ("ipv4", "ipv6", "ipv4_rand", "ipv6_rand"):
            return self._prepare_l3_ip(spec, context)
        if spec["l3"] in ("arp"):
            return self._prepare_l3_arp(spec, context)
        else:
            raise RuntimeError(f'unsupported l3: {spec["l3"]}')

    @abc.abstractmethod
    def _prepare_l4_udp_tcp_sctp(self, spec, context=None):
        """Prepare L4 scapy headers: UDP(), TCP(), SCTP()"""
        ...

    def _prepare_l4_icmp(self, spec, context=None):
        """Prepare L4 scapy headers: ICMP(), ICMPv6EchoRequest()"""
        if spec["l3"] == "ipv4":
            return [scapy.ICMP()]
        elif spec["l3"] == "ipv6":
            return [scapy.ICMPv6EchoRequest()]
        else:
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for icmp')

    def _prepare_l4_icmp_random(self, spec, context=None):
        """Prepare randomized L4 scapy headers: ICMP(), ICMPv6EchoRequest()"""
        if spec["l3"] == "ipv4":
            hdr = RandomICMPHeader()
        elif spec["l3"] == "ipv6":
            hdr = RandomICMPv6Header()
        else:
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for icmp')

        return [hdr()]

    def _prepare_l4_igmp(self, spec, context=None):
        """Prepare L4 scapy headers: IGMP(), ICMPv6MLQuery()"""
        if spec["l3"] == "ipv4":
            return [igmp.IGMP()]
        elif spec["l3"] == "ipv6":
            return [scapy.ICMPv6MLQuery()]
        else:
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for igmp')

    def _prepare_l4_igmp_random(self, spec, context=None):
        """Prepare randomized L4 scapy headers: IGMP(), ICMPv6MLQuery()"""
        if spec["l3"] == "ipv4":
            hdr = RandomIGMPHeader()
        elif spec["l3"] == "ipv6":
            hdr = RandomMLDHeader()
        else:
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for igmp')

        return [hdr()]

    @abc.abstractmethod
    def _prepare_l4_ndp(self, spec, context=None):
        """Prepare L4 scapy headers: ICMPv6ND_NS()"""
        ...

    def _prepare_l4(self, spec, context=None):
        """Prepare L4 scapy headers."""
        if "l4" not in spec:
            return []

        if spec["l4"] in ("udp", "tcp", "sctp", "udp_rand", "tcp_rand", "sctp_rand"):
            return self._prepare_l4_udp_tcp_sctp(spec, context)
        elif spec["l4"] == "icmp":
            return self._prepare_l4_icmp(spec, context)
        elif spec["l4"] == "icmp_rand":
            return self._prepare_l4_icmp_random(spec, context)
        elif spec["l4"] == "igmp":
            return self._prepare_l4_igmp(spec, context)
        elif spec["l4"] == "igmp_rand":
            return self._prepare_l4_igmp_random(spec, context)
        elif spec["l4"] == "ndp":
            return self._prepare_l4_ndp(spec, context)
        else:
            raise RuntimeError(f'unsupported l4: {spec["l4"]}')

    def _cross_headers(self, l2_list, l3_list, l4_list):
        """Do cartesian product of L2, L3 and L4 headers.

        For example:
        - L2 contains list of 2 headers (2 MAC addresses)
        - L3 contains list of 10 headers (2 dst IPs * 5 src IPs)
        - L4 contains list of 5 headers (5 dst ports * 1 src port)
        Then output will be 2 * 10 * 5 = 100 assembled scapy headers
        """
        assert len(l2_list) > 0, "no L2 headers"

        headers = []

        if len(l4_list) > 0:
            if len(l3_list) == 0:
                raise RuntimeError("missing l3 specification, but l4 was given")

            for l2 in l2_list:
                for l3 in l3_list:
                    for l4 in l4_list:
                        headers.append(l2 / l3 / l4)
        elif len(l3_list) > 0:
            for l2 in l2_list:
                for l3 in l3_list:
                    headers.append(l2 / l3)
        else:
            headers = l2_list

        return headers

    def _prepare_headers(self, spec, context=None):
        """Prepare scapy headers based on input specification."""
        l2_list = self._prepare_l2(spec, context)
        l3_list = self._prepare_l3(spec, context)
        l4_list = self._prepare_l4(spec, context)

        return self._cross_headers(l2_list, l3_list, l4_list)

    def _pkt_finalize(self, hdr, pkt_len, pkt_paylen):
        """Finalize packet - add padding to reach desired packet length."""
        # No payload
        if pkt_paylen is None and pkt_len is None:
            return hdr

        # Only payload length is set
        elif pkt_paylen is not None and pkt_len is None:
            return hdr / (pkt_paylen * "\x00")

        # Only packet length is set
        elif pkt_paylen is None and pkt_len is not None:
            if pkt_len < len(hdr):
                raise RuntimeError(f"pkt_len {pkt_len} is too small, required at least {len(hdr)}")

            return hdr / ((pkt_len - len(hdr)) * "\x00")

        # Both payload length and packet length is set
        else:
            if pkt_len < len(hdr):
                raise RuntimeError(f"pkt_len {pkt_len} is too small, required at least {len(hdr)}")
            if len(hdr) + pkt_paylen != pkt_len:
                raise RuntimeError(
                    f"pkt_len {pkt_len} does not match pkt_paylen {pkt_paylen} (+{len(hdr)})"
                )

            return hdr / (pkt_paylen * "\x00")

    def _prepare_pkts(self, spec, context=None):
        """Prepare scapy packets based on input specification."""
        headers = self._prepare_headers(spec, context)
        pkts = []

        pkt_len = spec.get("pkt_len", None)
        pkt_paylen = spec.get("pkt_paylen", None)

        for hdr in headers:
            pkts.append(self._pkt_finalize(hdr, pkt_len, pkt_paylen))

        return pkts
