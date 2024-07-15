"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Packet crafter for TRex traffic generator.
"""

import ipaddress
import logging
import uuid

import lbr_trex_client  # noqa: F401
import scapy.all as scapy
import trex.stl.trex_stl_packet_builder_scapy as trex_packet_builder

from . import abstract_packet_crafter, ipaddresses, ports


global_logger = logging.getLogger(__name__)


class TRexInstructionCrafter:
    """Helper class for TRexPacketCrafter to create Field Engine
    instructions for TRex traffic generator.
    """

    def build_instructions(
        self,
        fe_instructions,
        name,
        values,
        size,
        pkt_offset,
        offset_fixup=0,
        op="inc",
    ):
        """Create instructions and add them to instruction list.

        Parameters
        ----------
        fe_instructions : list
            Instruction list.
        name : str
            Name of instruction variable. Must be unique among other instructions.
        values : dict
            Values to be passed into ``trex_packet_builder.STLVmFlowVar`` object.
            It's expected to be either ``min_value`` + ``max_value`` or ``value_list``.
        size : int
            Number of bytes to rewrite. Can be 1, 2, 4 or 8. For example, to rewrite
            IPv4 address, ``size=4`` should be set.
        pkt_offset : str or int
            Offset where rewritting starts. Can be int (bytes from start of packet) or
            Scapy notation (eg. 'IPv6.dst')
        offset_fixup : int
            Add ``offset_fixup`` bytes to ``pkt_offset``. Can be useful for example when rewritting
            second half of 16B IPv6 address - then ``offset_fixup`` should be 8.
        op : str, optional
            Modifier of values. Possible options:
            - "inc" for incrementing distribution.
            - "dec" for decrementing distribution.
            - "random" for random distribution.
        """
        instr1 = trex_packet_builder.STLVmFlowVar(name, **values, size=size, op=op)
        instr2 = trex_packet_builder.STLVmWrFlowVar(
            name, pkt_offset=pkt_offset, offset_fixup=offset_fixup
        )
        fe_instructions.extend([instr1, instr2])

    def _prepare_ipv4_values(self, l3_addrs):
        """Prepare values for IPv4. See build_instructions.values parameter."""
        values = {}

        if l3_addrs.is_single_prefix():
            values["min_value"] = l3_addrs.first_ip()
            values["max_value"] = l3_addrs.last_ip()
        elif l3_addrs.is_ip_list():
            values["value_list"] = list(map(str, l3_addrs.addresses_as_list()))

        return values

    def _prepare_ipv6_values(self, l3_addrs):
        """Prepare values for IPv6. See build_instructions.values parameter.
        Returns tuple of 2 values for first and second half of IPv6.
        Some values might be empty.
        """
        first_half = {}
        second_half = {}

        first_ip = int(ipaddress.IPv6Address(l3_addrs.first_ip()))
        last_ip = int(ipaddress.IPv6Address(l3_addrs.last_ip()))

        if l3_addrs.is_single_prefix():
            xor = first_ip ^ last_ip
            if xor.bit_length() > 64:
                raise RuntimeError(
                    "Generating IPv6 prefix with prefix length in "
                    "0-63 range is not currently supported"
                )

            first_half, second_half = self._prepare_ipv6_prefix_values(first_ip, last_ip)
        elif l3_addrs.is_ip_list():
            first_half, second_half = self._prepare_ipv6_list_values(l3_addrs)

        return (first_half, second_half)

    def _prepare_ipv6_list_values(self, l3_addrs):
        """Prepare values for list of IPv6 addresses."""
        first_half = {"value_list": []}
        second_half = {"value_list": []}

        for addr in l3_addrs.addresses_as_list():
            first_half["value_list"].append(int.from_bytes(addr.packed[0:8], byteorder="big"))
            second_half["value_list"].append(int.from_bytes(addr.packed[8:16], byteorder="big"))

        return (first_half, second_half)

    def _prepare_ipv6_prefix_values(self, first_ip, last_ip):
        """Prepare values for single IPv6 prefix that has prefix length in 64-128 range."""
        first_half = {}
        second_half = {}

        # TRex allows only 8B per instruction. If 16B IPv6 address has
        # non-zero first half (eg. 2001::aaaa), it must be zeroed
        # so that only second half of address is left (::aaaa).
        second_half_bitmask = 0xFFFFFFFFFFFFFFFF
        second_half["min_value"] = first_ip & second_half_bitmask
        second_half["max_value"] = last_ip & second_half_bitmask

        if second_half["max_value"] == 0xFFFFFFFFFFFFFFFF:
            # TRex currently crashes when (2^64)-1 is set as a value (all bits are 1).
            # Workaround: lower value by 1.
            # Should be removed when fixed TRex version is released.
            second_half["max_value"] -= 1
            global_logger.warning(
                f"Cannot generate {ipaddress.IPv6Address(last_ip)} due to bug in TRex"
            )

        return (first_half, second_half)

    def _build_arp_instructions(self, fe_instructions, l3_addrs):
        """Build ARP instructions."""
        values = self._prepare_ipv4_values(l3_addrs)
        self.build_instructions(fe_instructions, str(uuid.uuid4()), values, 4, "ARP.pdst")

    def _build_ipv4_instructions(self, fe_instructions, l3_addrs, direction):
        """Build IPv4 instructions."""
        values = self._prepare_ipv4_values(l3_addrs)
        self.build_instructions(fe_instructions, str(uuid.uuid4()), values, 4, f"IP.{direction}")

    def _build_ipv6_instructions(self, fe_instructions, l3_addrs, direction):
        """Build IPv6 instructions.

        IPv6 can build 2 instructions because single instruction
        can rewrite maximum of 8B, but IPv6 has 16B.
        """

        first_half, second_half = self._prepare_ipv6_values(l3_addrs)

        if l3_addrs.is_single_prefix():
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), second_half, 8, f"IPv6.{direction}", 8
            )
        elif l3_addrs.is_ip_list():
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), first_half, 8, f"IPv6.{direction}"
            )
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), second_half, 8, f"IPv6.{direction}", 8
            )

    def prepare_l3_instructions(self, spec, l3_addrs, direction):
        """Create Field Engine instructions for L3 layer."""
        fe_instructions = []

        # Single IP is provided by Scapy packet template
        if l3_addrs.is_single_ip():
            return fe_instructions

        if spec["l3"] == "ipv4":
            self._build_ipv4_instructions(fe_instructions, l3_addrs, direction)
        elif spec["l3"] == "arp":
            self._build_arp_instructions(fe_instructions, l3_addrs)
        elif spec["l3"] == "ipv6":
            self._build_ipv6_instructions(fe_instructions, l3_addrs, direction)

        if "l4" not in spec and spec["l3"] == "ipv4":
            csum_instruction = trex_packet_builder.STLVmFixIpv4(
                offset=self._get_l3_offsets(spec["l3"]),
            )
            fe_instructions.extend([csum_instruction])

        return fe_instructions

    def prepare_ndp_instructions(self, l3_addrs):
        """Create Field Engine instructions for NDP header."""
        fe_instructions = []
        first_half, second_half = self._prepare_ipv6_values(l3_addrs)

        if l3_addrs.is_single_prefix():
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), second_half, 8, f"ICMPv6ND_NS.tgt", 8
            )
        else:
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), first_half, 8, f"ICMPv6ND_NS.tgt"
            )
            self.build_instructions(
                fe_instructions, str(uuid.uuid4()), second_half, 8, f"ICMPv6ND_NS.tgt", 8
            )

        return fe_instructions

    def _get_l4_offsets(self, l4):
        """Get L4 offsets required by Field Engine instructions."""
        if l4 == "udp":
            l4_offset = "UDP"
        elif l4 == "tcp":
            l4_offset = "TCP"
        elif l4 == "sctp":
            l4_offset = "SCTP"

        return l4_offset

    def _get_l3_offsets(self, l3):
        """Get L3 offsets required by Field Engine instructions."""
        if l3 == "ipv4":
            l3_offset = "IP"
        elif l3 == "ipv6":
            l3_offset = "IPv6"

        return l3_offset

    def prepare_l4_instructions(self, spec, l4_ports, direction, op="inc"):
        """Create Field Engine instructions for L4 layer."""
        fe_instructions = []
        values = {}
        l4_offset = self._get_l4_offsets(spec["l4"])
        dir_offset = ".sport" if direction == "src" else ".dport"

        if l4_ports.is_port_range():
            values["min_value"] = l4_ports.ports_as_range()[0]
            values["max_value"] = l4_ports.ports_as_range()[1]
        else:
            values["value_list"] = l4_ports.ports_as_list()
        self.build_instructions(
            fe_instructions, l4_offset + "_" + direction, values, 2, l4_offset + dir_offset, op=op
        )

        if spec["l4"] != "sctp":
            if spec["l4"] == "tcp":
                l4_type = trex_packet_builder.CTRexVmInsFixHwCs.L4_TYPE_TCP
            elif spec["l4"] == "udp":
                l4_type = trex_packet_builder.CTRexVmInsFixHwCs.L4_TYPE_UDP

            csum_instruction = trex_packet_builder.STLVmFixChecksumHw(
                l3_offset=self._get_l3_offsets(spec["l3"]),
                l4_offset=self._get_l4_offsets(spec["l4"]),
                l4_type=l4_type,
            )
            fe_instructions.extend([csum_instruction])

        return fe_instructions


class TRexPacketCrafter(abstract_packet_crafter.AbstractPacketCrafter):
    """Packet crafter for TRex traffic generator.

    Crafter provides a single scapy packet (template) with
    Field Engine (FE) instructions for TRex generator.

    If L3/L4 source or destination has only a single value (single
    IP address or port), then this value is included in Scapy packet.

    If it has multiple values (list, range, etc.), then header field
    is empty (0 for port or 0.0.0.0/:: IP address) as values will be
    replaced according to FE instructions.

    The reason for this split is performance as FE is computed in software.
    For maximum performance it's better to split complex stream into
    single-value streams and do not use FE instructions.

    For example, following stream::

        l3_src: ["10.0.0.0", "10.0.0.1"]
        l3_dst: "20.0.0.0"
        l4_src: [4000, 5000]
        l4_dst: 80

    Can be split into 2 * 1 * 2 * 1 = 4 single-value streams::

        l3_src: "10.0.0.0", l3_dst: "20.0.0.0", l4_src: 4000, l4_dst: 80
        l3_src: "10.0.0.1", l3_dst: "20.0.0.0", l4_src: 4000, l4_dst: 80
        l3_src: "10.0.0.0", l3_dst: "20.0.0.0", l4_src: 5000, l4_dst: 80
        l3_src: "10.0.0.1", l3_dst: "20.0.0.0", l4_src: 5000, l4_dst: 80

    This optimalization should be used only in performance measuring, it's
    not recommended for standard tests.
    """

    def __init__(self):
        super().__init__()
        self._fe_builder = TRexInstructionCrafter()

    def _prepare_l3_ip(self, spec, context=None):
        """Prepare L3 scapy headers: IP(), IPv6()"""
        if spec["l3"] == "ipv4":
            IP_hdr = scapy.IP
            IPAddresses = ipaddresses.IPv4Addresses
            src_ip = "0.0.0.0"
            dst_ip = "0.0.0.0"
        elif spec["l3"] == "ipv6":
            IP_hdr = scapy.IPv6
            IPAddresses = ipaddresses.IPv6Addresses
            src_ip = "::"
            dst_ip = "::"
        else:
            RuntimeError(f'unsupported l3: {spec["l3"]}')

        if "l3_src" in spec:
            addrs = IPAddresses(spec["l3_src"])
            src_ip = addrs.first_ip()
            l3_src_instr = self._fe_builder.prepare_l3_instructions(spec, addrs, "src")
            context.extend(l3_src_instr)

        if "l3_dst" in spec:
            addrs = IPAddresses(spec["l3_dst"])
            dst_ip = addrs.first_ip()
            l3_dst_instr = self._fe_builder.prepare_l3_instructions(spec, addrs, "dst")
            context.extend(l3_dst_instr)

        return [IP_hdr(src=src_ip, dst=dst_ip)]

    def _prepare_l3_arp(self, spec, context=None):
        """Prepare L3 scapy ARP header"""
        if spec["l3"] != "arp":
            RuntimeError(f'unsupported l3: {spec["l3"]}')

        dst_ip = "0.0.0.0"

        if "l3_dst" in spec and ipaddresses.IPv4Addresses(spec["l3_dst"]).is_single_ip():
            dst_ip = str(ipaddresses.IPv4Addresses(spec["l3_dst"]).addresses_as_list()[0])

        l3_dst_instr = self._fe_builder.prepare_l3_instructions(
            spec, ipaddresses.IPv4Addresses(spec["l3_dst"]), "dst"
        )
        context.extend(l3_dst_instr)

        return [scapy.ARP(pdst=dst_ip)]

    def _get_l4_flags(self, flags):
        """Get L4 flags as one string."""
        if isinstance(flags, list):
            return "".join([i.value for i in flags])

        return flags.value

    def _prepare_l4_udp_tcp_sctp(self, spec, context=None):
        """Prepare L4 scapy headers: UDP(), TCP(), SCTP()"""
        if spec["l4"] == "udp":
            L4_hdr = scapy.UDP
        elif spec["l4"] == "tcp":
            L4_hdr = scapy.TCP
        elif spec["l4"] == "sctp":
            L4_hdr = scapy.SCTP
        else:
            RuntimeError(f'unsupported l4: {spec["l4"]}')

        src_port = 0
        dst_port = 0

        if "l4_src" in spec:
            l4_ports = ports.L4Ports(spec["l4_src"])

            if l4_ports.is_single_port():
                src_port = l4_ports.ports()

            l4_src_instr = self._fe_builder.prepare_l4_instructions(
                spec, l4_ports, "src", op=spec.get("l4_op", "inc")
            )
            context.extend(l4_src_instr)

        if "l4_dst" in spec:
            l4_ports = ports.L4Ports(spec["l4_dst"])

            if l4_ports.is_single_port():
                dst_port = l4_ports.ports()

            l4_dst_instr = self._fe_builder.prepare_l4_instructions(
                spec, l4_ports, "dst", op=spec.get("l4_op", "inc")
            )
            context.extend(l4_dst_instr)

        if spec["l4"] == "tcp":
            return [
                L4_hdr(sport=src_port, dport=dst_port, flags=self._get_l4_flags(spec["l4_flags"]))
            ]

        return [L4_hdr(sport=src_port, dport=dst_port)]

    def _prepare_l4_ndp(self, spec, context=None):
        """Prepare L4 scapy headers: ICMPv6ND_NS()"""
        if spec["l3"] != "ipv6":
            raise RuntimeError(f'incompatible l3 type {spec["l3"]} for ndp')

        dst_ip = "::"
        if "l3_dst" in spec and ipaddresses.IPv6Addresses(spec["l3_dst"]).is_single_ip():
            dst_ip = str(ipaddresses.IPv6Addresses(spec["l3_dst"]).addresses_as_list()[0])

        l4_dst_instr = self._fe_builder.prepare_ndp_instructions(
            ipaddresses.IPv6Addresses(spec["l3_dst"])
        )
        context.extend(l4_dst_instr)

        return [scapy.ICMPv6ND_NS(tgt=dst_ip)]

    def packet_with_fe_instructions(self, spec):
        """Return one scapy packet and list of TRex Field Engine instructions
        based on specification.

        Scapy packet works as a template. It contains specified headers
        in correct order. Certain header values will be replaced by TRex
        according to instructions. Instructions define new values
        and their order.

        Specification allows user to define only one type of packet at
        the time and so only one packet (template) is returned.

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
                Can be 'ipv4', 'ipv6' or 'arp' (for NDP see ``l4``).
            l3_src : various
                Source IP addresses. Following formats are supported:
                ``10.0.0.0``, ``2001:db8::/32``, ``{first='10.0.0.0', count=150, step=1}``,
                ``random_types.RandomIP`` or ``list`` of previous formats. For more info see
                ``packet_crafter.ipaddresses.IPv4Addresses`` and
                ``packet_crafter.ipaddresses.IPv6Addresses``.
            l3_dst : various
                Destination IP address(es). Same format as ``l3_src``.
            l4 : str
                Can be 'tcp', 'udp', 'sctp', 'icmp', 'igmp' or 'ndp' (IPv6 only).
            l4_src : various
                Source port(s). Following formats are supported:
                10, (10-20), [10,12,17,20]. For more info see ``packet_crafter.ports.L4Ports``.
            l4_dst : int or list or tuple
                Destination port(s). Same format as ``l4_src``.
            l4_op : str, optional
                Modifier of L4 values (both src and dst). Possible options:
                - "inc" for incrementing distribution (default).
                - "dec" for decrementing distribution.
                - "random" for random distribution.
            l4_flag : TRexL4Flag or list(TRexL4Flag), optional
                Any combination of TCP flags.
            pkt_len : int
                Packet length (without Ethernet's FCS).
            pkt_paylen : int
                Fixed number of bytes to add as payload. If ``pkt_len`` is set, then
                packet size without payload + ``pkt_paylen`` must match ``pkt_len``.

        Returns
        ------
        tuple(scapy.layers.l2.Ether, list)
            One Scapy packet and a list of TRex Field Engine instructions.
        """

        fe_instructions = []
        packets = self._prepare_pkts(spec, fe_instructions)
        assert len(packets) == 1

        return (packets[0], fe_instructions)
