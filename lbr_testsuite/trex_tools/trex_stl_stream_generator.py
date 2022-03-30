"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET

Class containing definition of commonly used TRex stateless
packet streams and their packet checking methods.
"""


import logging
from ipaddress import IPv4Address, IPv6Address


global_logger = logging.getLogger(__name__)

import lbr_trex_client.paths  # noqa: F401
from scapy.layers.dns import *
from trex.stl.api import *

from .trex_instances import TRex_Instances as TRex


class TRex_Stl_Stream_Generator:
    """Class containing definition of commonly used packet streams
    and their packet checking methods.

    Streams can be costumized according to input arguments.
    Only commonly used parameters were selected.
    TRex and Scapy support more customization and class can be extended
    if new requirements appear. Some TRex documentation can be found
    `here <https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/profile_code.html>`_.

    Example of stream usage::

        client_traffic_stream = TRex_Stl_Stream_Generator(traffic_trex,
            port=0,
            stream_pps='8mpps'
        )
        traffic_trex.add_streams(client_traffic_stream.udp4_stream(), ports=0)

        server_traffic_stream = TRex_Stl_Stream_Generator(traffic_trex,
            port=1,
            packet_size=512,
            src_ipv4_from='10.0.1.1',
            src_ipv4_to='10.0.1.62',
            dst_ipv4_from='10.0.0.1',
            dst_ipv4_to='10.0.0.254',
            stream_bps_L2='5gbps'
        )
        traffic_trex.add_streams(server_traffic_stream.udp4_stream(), ports=1)

    Example of checking stream packets::

        traffic_trex.start(ports=0, duration=10)  # Client traffic generation
        # Service mode on server is needed for packet capture, but it lowers performance
        traffic_trex.set_service_mode(ports=1)
        traffic_trex.start(ports=1, duration=10, force=True)  # Server traffic generation

        # More info about capture method:
        # https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/client_code.html#trex.stl.trex_stl_client.STLClient.start_capture
        capt = traffic_trex.start_capture(rx_ports=1, limit=1000, mode='fixed')
        time.sleep(1)
        captured_packets = []
        traffic_trex.stop_capture(capt['id'], output=captured_packets)

        for packet in captured_packets:
            if client_traffic_stream.is_udp4_stream_packet(packet):
                print("Packet is part of client's udp4_stream().")

    Parameters
    ----------
    trex_handler : STLClient
        TRex handler.
    port : int, optional
        Physical port used for stream. Used to determine if VLAN
        needs to be added or not.
    packet_padding : bool, optional
        Pad packets to *packet_size*.
    packet_size : int, optional
        Packet size without Ethernet's FCS, as FCS processing is
        offloaded to HW.
        This means that actual sent/received packets are 4B bigger.

        .. warning::
            It seems like some packet sizes (even without
            padding) can cause overwriting of packet fields, resulting
            in failed tests.
    src_ipv4_from : str, optional
        IPv4 source address - beginning of range.
    src_ipv4_to : str, optional
        IPv4 source address - end of range.
    src_ipv4_op : str, optional
        IPv4 source address - distribution (``random, inc, dec``).
    dst_ipv4_from : str, optional
        IPv4 destination address - beginning of range.
    dst_ipv4_to : str, optional
        IPv4 destination address - end of range.
    dst_ipv4_op : str, optional
        IPv4 destination address - distribution (``random, inc, dec``).

    ipv6_msb : str, optional
        MSB of IPv6 address. Field Engine can change only 32 bits of
        IPv6 address (because of 32bit tuple generator).
        Rest of bits is set by this value. See
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.udp6_stream`
        for example.
    src_ipv6_from : str, optional
        IPv6 source address (32 bits) - beginning of range.
        Use IPv4 notation.
    src_ipv6_to : str, optional
        IPv6 source address (32 bits) - end of range.
        Use IPv4 notation.
    src_ipv6_op : str, optional
        IPv6 source address - distribution (``random, inc, dec``).
    dst_ipv6_from : str, optional
        IPv6 destination address (32 bits) - beginning of range.
        Use IPv4 notation.
    dst_ipv6_to : str, optional
        IPv6 destination address (32 bits) - end of range.
        Use IPv4 notation.
    dst_ipv6_op : str, optional
        IPv6 destination address - distribution (``random, inc, dec``).

    src_port_from : int, optional
        Source port - beginning of range.
    src_port_to : int, optional
        Source port - end of range.
    src_port_op : int, optional
        Source port - distribution (``random, inc, dec``).
    dst_port_from : int, optional
        Destination port - beginning of range.
    dst_port_to : int, optional
        Destination port - end of range.
    dst_port_op : int, optional
        Destination port - distribution (``random, inc, dec``).

    tcp_flags : str, optional
        TCP flags. Example: ``'SA'`` for SYN+ACK.

    stream_mode : str, optional
        | Packet stream mode:
        | ``STLTXCont`` - Continuous packet generation until stopped.
        | ``STLTXSingleBurst`` - Only single stream burst, *total_pkts* must be set.

        More information can be found at this
        `link <https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/profile_code.html#stlstream-modes>`_.
    stream_pps : Union[int, str], optional
        Generate N packets per second. Example: 80000 or '80kpps'
        (see :meth:`~trex_tools.trex_instances.TRex_Instances.u2i`).
        Only **one** of *stream_pps*, *stream_bps_L2* or
        *stream_percentage* can be set.
    stream_bps_L2 : Union[int, str], optional
        Generate N bits per second on L2 layer.
        Example: 3330000000 or '3.33gbps' (see
        :meth:`~trex_tools.trex_instances.TRex_Instances.u2i`).
        Only **one** of *stream_pps*, *stream_bps_L2* or
        *stream_percentage* can be set.
    stream_percentage : Union[int, str], optional
        Generate at the rate of N percent of port maximum bandwidth
        (in bits per second). Example: 85 or '85%'.
        Only **one** of *stream_pps`, *stream_bps_L2* or
        *stream_percentage* can be set.
    total_pkts : int, optional
        Total number of packets to be generated. Works only with
        *stream_mode* set to ``STLTXSingleBurst``.
    """

    def __init__(
        self,
        trex_handler,
        port=0,
        packet_size=222,
        packet_padding=True,
        src_ipv4_from="10.0.0.1",
        src_ipv4_to="10.0.0.254",
        dst_ipv4_from="10.0.1.1",
        dst_ipv4_to="10.0.1.62",
        src_ipv4_op="random",
        dst_ipv4_op="random",
        ipv6_msb="2001:db8::",
        src_ipv6_from="0.0.0.1",
        src_ipv6_to="0.0.0.254",
        dst_ipv6_from="0.0.1.1",
        dst_ipv6_to="0.0.1.62",
        src_ipv6_op="random",
        dst_ipv6_op="random",
        src_port_from=1025,
        src_port_to=65000,
        dst_port_from=1025,
        dst_port_to=65000,
        src_port_op="random",
        dst_port_op="random",
        tcp_flags="S",
        stream_mode="STLTXCont",
        stream_pps=None,
        stream_bps_L2=None,
        stream_percentage=None,
        total_pkts=None,
        **kwargs,
    ):

        if not isinstance(trex_handler, STLClient):
            raise ValueError(
                f"TRex_handler parameter needs to be STLClient type! Instead got {type(trex_handler)}"
            )

        # Define all parameters as class attributes
        for param, value in locals().items():
            if param != "self":
                setattr(self, param, value)

        if isinstance(stream_pps, str):
            self.stream_pps = TRex.u2i(self.stream_pps)
        if isinstance(stream_bps_L2, str):
            self.stream_bps_L2 = TRex.u2i(self.stream_bps_L2)
        if isinstance(stream_percentage, str):
            self.stream_percentage = TRex.u2i(self.stream_percentage)

        if packet_padding:
            if packet_size < 60:
                raise ValueError(
                    "Minimum allowed packet_size is 60B (+4B FCS automatically added by HW)."
                )

        self.tcp_flags_s2i = {
            "F": 0x01,
            "S": 0x02,
            "R": 0x04,
            "P": 0x08,
            "A": 0x10,
            "U": 0x20,
            "E": 0x40,
            "C": 0x80,
        }

    def _create_frame(self):

        # MAC addresses are taken from TRex configuration file/interface by default
        frame = Ether()

        # Automatically add VLAN if needed
        if self.trex_handler.get_port_attr(self.port)["vlan"] != "-":
            frame = frame / Dot1Q(vlan=self.trex_handler.get_port_attr(self.port)["vlan"])

        return frame

    def _add_padding(self, packet):

        padding = ""

        if self.packet_padding and self.packet_size > len(packet):
            padding = "TRexPadding" * 140  # Enough to pad 1500B
            padding = padding[: (self.packet_size - len(packet))]

        return padding

    def _create_stl_stream(self, packet, vm):

        if self.stream_mode == "STLTXCont":
            if self.stream_pps:
                mode = STLTXCont(pps=self.stream_pps)
            elif self.stream_bps_L2:
                mode = STLTXCont(bps_L2=self.stream_bps_L2)
            elif self.stream_percentage:
                mode = STLTXCont(percentage=self.stream_percentage)

        elif self.stream_mode == "STLTXSingleBurst":
            if self.stream_pps:
                mode = STLTXSingleBurst(pps=self.stream_pps, total_pkts=self.total_pkts)
            elif self.stream_bps_L2:
                mode = STLTXSingleBurst(bps_L2=self.stream_bps_L2, total_pkts=self.total_pkts)
            elif self.stream_percentage:
                mode = STLTXSingleBurst(
                    percentage=self.stream_percentage, total_pkts=self.total_pkts
                )

        return STLStream(
            packet=STLPktBuilder(pkt=packet / self._add_padding(packet), vm=vm), mode=mode
        )

    def _get_expected_packet_size(self, base_packet):

        if self.packet_padding and self.packet_size > len(base_packet):
            return self.packet_size
        else:
            # If base packet size is below 60B (+4B FCS), it is automatically padded
            if len(base_packet) <= 60:
                return 60
            else:
                return len(base_packet)

    def _v4_to_v6(self, ip):

        numbers = list(map(int, ip.split(".")))
        return self.ipv6_msb + "{:02x}{:02x}:{:02x}{:02x}".format(*numbers)

    def _ips_in_range(self, src_ip, dst_ip, ipv6=False):

        if not ipv6:
            return IPv4Address(self.src_ipv4_from) <= IPv4Address(src_ip) <= IPv4Address(
                self.src_ipv4_to
            ) and IPv4Address(self.dst_ipv4_from) <= IPv4Address(dst_ip) <= IPv4Address(
                self.dst_ipv4_to
            )
        else:
            src_from = self._v4_to_v6(self.src_ipv6_from)
            dst_from = self._v4_to_v6(self.dst_ipv6_from)
            src_to = self._v4_to_v6(self.src_ipv6_to)
            dst_to = self._v4_to_v6(self.dst_ipv6_to)

            return IPv6Address(src_from) <= IPv6Address(src_ip) <= IPv6Address(
                src_to
            ) and IPv6Address(dst_from) <= IPv6Address(dst_ip) <= IPv6Address(dst_to)

    def _ports_in_range(self, src_port=None, dst_port=None):

        ret = True
        if src_port:
            ret &= self.src_port_from <= src_port <= self.src_port_to
        if dst_port:
            ret &= self.dst_port_from <= dst_port <= self.dst_port_to

        return ret

    def udp4_stream(self):
        """Create IPv4/UDP stream using Scapy and TRex's Field Engine.

        Returns
        -------
        STLStream
            TRex stream.
        """

        # TRex uses Scapy for basic packet definition
        packet = self._create_frame() / IP() / UDP()

        # TRex's Field Engine (FE) - change packet fields (IPs, ports, ...) per packet during traffic generation
        # For more info see https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/field_engine.html
        # or https://trex-tgn.cisco.com/trex/doc/trex_stateless.html#_tutorial_field_engine_syn_attack
        vm = STLScVmRaw(
            [
                # Define values
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                # Write values to packet
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="UDP.sport"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="UDP.dport"),
                # Let HW recompute checksum
                STLVmFixChecksumHw(
                    l3_offset="IP", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_udp4_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.udp4_stream`.
        """

        pkt = Ether(packet["binary"])

        if IP in pkt and UDP in pkt:
            if (
                self._ips_in_range(pkt["IP"].src, pkt["IP"].dst)
                and self._ports_in_range(pkt["UDP"].sport, pkt["UDP"].dport)
                and len(pkt) == self._get_expected_packet_size(self._create_frame() / IP() / UDP())
            ):
                return True

        return False

    def udp6_stream(self):
        """Create IPv6/UDP stream.

        IPv6 MSBs are set to a fixed value, only 32 bits can be changed
        by Field Engine (because of 32bit tuple generator). In this
        case it's lowest 32 bits.
        Example: With *ipv6_msb* set to ``2001:db8::``,
        *ipv6_from* to ``0.0.0.1`` and *ipv6_to* to ``0.0.10.255``,
        then the final IPv6 range will translate into
        ``2001:db8::1 - 2001:db8::AFF``

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = self._create_frame() / IPv6(src=self.ipv6_msb, dst=self.ipv6_msb) / UDP()

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv6_from,
                    max_value=self.src_ipv6_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv6_from,
                    max_value=self.dst_ipv6_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(
                    fv_name="ip_src", pkt_offset="IPv6.src", offset_fixup=12
                ),  # Write only lowest 32 bits of address
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IPv6.dst", offset_fixup=12),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="UDP.sport"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="UDP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IPv6", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_udp6_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.udp6_stream`.
        """

        pkt = Ether(packet["binary"])

        if IPv6 in pkt and UDP in pkt:
            if (
                self._ips_in_range(pkt["IPv6"].src, pkt["IPv6"].dst, True)
                and self._ports_in_range(pkt["UDP"].sport, pkt["UDP"].dport)
                and len(pkt)
                == self._get_expected_packet_size(self._create_frame() / IPv6() / UDP())
            ):
                return True

        return False

    def tcp4_stream(self):
        """Create IPv4/TCP stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = self._create_frame() / IP() / TCP(flags=self.tcp_flags)

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="TCP.sport"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="TCP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IP", l4_offset="TCP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_TCP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_tcp4_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.tcp4_stream`.
        """

        pkt = Ether(packet["binary"])

        flags_value = 0
        for i in self.tcp_flags:
            flags_value += self.tcp_flags_s2i[i]

        if IP in pkt and TCP in pkt:
            if (
                self._ips_in_range(pkt["IP"].src, pkt["IP"].dst)
                and self._ports_in_range(pkt["TCP"].sport, pkt["TCP"].dport)
                and pkt["TCP"].flags == flags_value
                and len(pkt) == self._get_expected_packet_size(self._create_frame() / IP() / TCP())
            ):
                return True

        return False

    def tcp6_stream(self):
        """Create IPv6/TCP stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IPv6(src=self.ipv6_msb, dst=self.ipv6_msb)
            / TCP(flags=self.tcp_flags)
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv6_from,
                    max_value=self.src_ipv6_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv6_from,
                    max_value=self.dst_ipv6_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IPv6.src", offset_fixup=12),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IPv6.dst", offset_fixup=12),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="TCP.sport"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="TCP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IPv6", l4_offset="TCP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_TCP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_tcp6_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.tcp6_stream`.
        """

        pkt = Ether(packet["binary"])

        flags_value = 0
        for i in self.tcp_flags:
            flags_value += self.tcp_flags_s2i[i]

        if IPv6 in pkt and TCP in pkt:
            if (
                self._ips_in_range(pkt["IPv6"].src, pkt["IPv6"].dst, True)
                and self._ports_in_range(pkt["TCP"].sport, pkt["TCP"].dport)
                and pkt["TCP"].flags == flags_value
                and len(pkt)
                == self._get_expected_packet_size(self._create_frame() / IPv6() / TCP())
            ):
                return True

        return False

    def icmp4_stream(self):
        """Create ICMPv4 stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = self._create_frame() / IP() / ICMP()

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmFixIpv4(offset="IP"),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_icmp4_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.icmp4_stream`.
        """

        pkt = Ether(packet["binary"])

        if IP in pkt and ICMP in pkt:
            if (
                self._ips_in_range(pkt["IP"].src, pkt["IP"].dst)
                and pkt["ICMP"]
                and len(pkt) == self._get_expected_packet_size(self._create_frame() / IP() / ICMP())
            ):
                return True

        return False

    def icmp6_stream(self):
        """Create ICMPv6 stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame() / IPv6(src=self.ipv6_msb, dst=self.ipv6_msb) / ICMPv6EchoRequest()
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv6_from,
                    max_value=self.src_ipv6_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv6_from,
                    max_value=self.dst_ipv6_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IPv6.src", offset_fixup=12),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IPv6.dst", offset_fixup=12),
                STLVmFixIcmpv6(l3_offset="IPv6", l4_offset=ICMPv6EchoRequest().name),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_icmp6_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.icmp6_stream`.
        """

        pkt = Ether(packet["binary"])

        if IPv6 in pkt:
            if (
                self._ips_in_range(pkt["IPv6"].src, pkt["IPv6"].dst, True)
                and pkt["IPv6"].nh == 58
                and len(pkt)
                == self._get_expected_packet_size(self._create_frame() / IPv6() / ICMP())
            ):
                return True

        return False

    def dns4_query_stream(self):
        """Create IPv4/UDP/DNS query stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IP()
            / UDP(dport=53)
            / DNS(qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"))
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="UDP.sport"),
                STLVmFixChecksumHw(
                    l3_offset="IP", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_dns4_query_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.dns4_query_stream`.
        """

        pkt = Ether(packet["binary"])

        # Sometimes padding of non-DNS packet can be parsed as DNS header (when src/dst
        # port is 53 or 5353), this can lead to WARNING messages like
        # "wrong value: DNS.qdcount=30840". This should be suppressed.
        prev_level = logging.getLogger("scapy.runtime").getEffectiveLevel()
        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

        if IP in pkt and UDP in pkt and DNS in pkt and DNSQR in pkt:
            logging.getLogger("scapy.runtime").setLevel(prev_level)

            if (
                self._ips_in_range(pkt["IP"].src, pkt["IP"].dst)
                and self._ports_in_range(src_port=pkt["UDP"].sport)
                and pkt["UDP"].dport == 53
                and
                # For type value see https://www.iana.org/assignments/dns-parameters/dns-parameters.xhtml#dns-parameters-4
                pkt["DNS"].qd.qtype == 255
                and pkt["DNS"].qd.qname == b"trex-tgn.cisco.com."
                and len(pkt)  # Dot after .com
                == self._get_expected_packet_size(
                    self._create_frame() / IP() / UDP() / DNS(qd=DNSQR(qname="trex-tgn.cisco.com"))
                )
            ):
                return True

        logging.getLogger("scapy.runtime").setLevel(prev_level)
        return False

    def dns4_response_stream(self):
        """Create IPv4/UDP/DNS response stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IP()
            / UDP(sport=53)
            / DNS(
                qr=1,
                qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"),
                an=DNSRR(rrname="trex-tgn.cisco.com", type="A", rdata="10.10.10.10"),
            )
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="UDP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IP", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_dns4_response_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.dns4_response_stream`.
        """

        pkt = Ether(packet["binary"])

        prev_level = logging.getLogger("scapy.runtime").getEffectiveLevel()
        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

        if IP in pkt and UDP in pkt and DNS in pkt and DNSQR in pkt and DNSRR in pkt:
            logging.getLogger("scapy.runtime").setLevel(prev_level)

            if (
                self._ips_in_range(pkt["IP"].src, pkt["IP"].dst)
                and self._ports_in_range(dst_port=pkt["UDP"].dport)
                and pkt["UDP"].sport == 53
                and pkt["DNS"].qd.qtype == 255
                and pkt["DNS"].qd.qname == b"trex-tgn.cisco.com."
                and pkt["DNS"].an.type == 1
                and pkt["DNS"].an.rrname == b"trex-tgn.cisco.com."
                and pkt["DNS"].an.rdata == "10.10.10.10"
                and len(pkt)
                == self._get_expected_packet_size(
                    self._create_frame()
                    / IP()
                    / UDP()
                    / DNS(
                        qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"),
                        an=DNSRR(rrname="trex-tgn.cisco.com", rdata="10.10.10.10"),
                    )
                )
            ):
                return True

        logging.getLogger("scapy.runtime").setLevel(prev_level)
        return False

    def dns6_response_stream(self):
        """Create IPv6/UDP/DNS response stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IPv6(src=self.ipv6_msb, dst=self.ipv6_msb)
            / UDP(sport=53)
            / DNS(
                qr=1,
                qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"),
                an=DNSRR(rrname="trex-tgn.cisco.com", type="AAAA", rdata="AAAA::B"),
            )
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv6_from,
                    max_value=self.src_ipv6_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv6_from,
                    max_value=self.dst_ipv6_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IPv6.src", offset_fixup=12),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IPv6.dst", offset_fixup=12),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="UDP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IPv6", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_dns6_response_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.dns6_response_stream`.
        """

        pkt = Ether(packet["binary"])

        prev_level = logging.getLogger("scapy.runtime").getEffectiveLevel()
        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

        if IPv6 in pkt and UDP in pkt and DNS in pkt and DNSQR in pkt and DNSRR in pkt:
            logging.getLogger("scapy.runtime").setLevel(prev_level)

            if (
                self._ips_in_range(pkt["IPv6"].src, pkt["IPv6"].dst, True)
                and self._ports_in_range(dst_port=pkt["UDP"].dport)
                and pkt["UDP"].sport == 53
                and pkt["DNS"].qd.qtype == 255
                and pkt["DNS"].qd.qname == b"trex-tgn.cisco.com."
                and pkt["DNS"].an.type == 28
                and pkt["DNS"].an.rrname == b"trex-tgn.cisco.com."
                and pkt["DNS"].an.rdata == "aaaa::b"
                and len(pkt)  # rdata must be lowercase
                == self._get_expected_packet_size(
                    self._create_frame()
                    / IPv6()
                    / UDP()
                    / DNS(
                        qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"),
                        an=DNSRR(rrname="trex-tgn.cisco.com", type="AAAA", rdata="AAAA::B"),
                    )
                )
            ):
                return True

        logging.getLogger("scapy.runtime").setLevel(prev_level)
        return False

    def dns6_query_stream(self):
        """Create IPv6/UDP/DNS stream.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IPv6(src=self.ipv6_msb, dst=self.ipv6_msb)
            / UDP(dport=53)
            / DNS(qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"))
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv6_from,
                    max_value=self.src_ipv6_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv6_from,
                    max_value=self.dst_ipv6_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IPv6.src", offset_fixup=12),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IPv6.dst", offset_fixup=12),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="UDP.sport"),
                STLVmFixChecksumHw(
                    l3_offset="IPv6", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_dns6_query_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.dns6_query_stream`.
        """

        pkt = Ether(packet["binary"])

        prev_level = logging.getLogger("scapy.runtime").getEffectiveLevel()
        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

        if IPv6 in pkt and UDP in pkt and DNS in pkt and DNSQR in pkt:
            logging.getLogger("scapy.runtime").setLevel(prev_level)

            if (
                self._ips_in_range(pkt["IPv6"].src, pkt["IPv6"].dst, True)
                and self._ports_in_range(src_port=pkt["UDP"].sport)
                and pkt["UDP"].dport == 53
                and pkt["DNS"].qd.qtype == 255
                and pkt["DNS"].qd.qname == b"trex-tgn.cisco.com."
                and len(pkt)
                == self._get_expected_packet_size(
                    self._create_frame()
                    / IPv6()
                    / UDP()
                    / DNS(qd=DNSQR(qname="trex-tgn.cisco.com"))
                )
            ):
                return True

        logging.getLogger("scapy.runtime").setLevel(prev_level)
        return False

    def dns4_query_rand_dst_port_stream(self):
        """Create IPv4/UDP/DNS stream.

        Uses random values for both source and destination ports.

        Returns
        -------
        STLStream
            TRex stream.
        """

        packet = (
            self._create_frame()
            / IP()
            / UDP()
            / DNS(qd=DNSQR(qname="trex-tgn.cisco.com", qtype="ALL"))
        )

        vm = STLScVmRaw(
            [
                STLVmFlowVar(
                    "ip_src",
                    min_value=self.src_ipv4_from,
                    max_value=self.src_ipv4_to,
                    size=4,
                    op=self.src_ipv4_op,
                ),
                STLVmFlowVar(
                    "ip_dst",
                    min_value=self.dst_ipv4_from,
                    max_value=self.dst_ipv4_to,
                    size=4,
                    op=self.dst_ipv4_op,
                ),
                STLVmFlowVar(
                    name="sport",
                    min_value=self.src_port_from,
                    max_value=self.src_port_to,
                    size=2,
                    op=self.src_port_op,
                ),
                STLVmFlowVar(
                    name="dport",
                    min_value=self.dst_port_from,
                    max_value=self.dst_port_to,
                    size=2,
                    op=self.dst_port_op,
                ),
                STLVmWrFlowVar(fv_name="ip_src", pkt_offset="IP.src"),
                STLVmWrFlowVar(fv_name="ip_dst", pkt_offset="IP.dst"),
                STLVmWrFlowVar(fv_name="sport", pkt_offset="UDP.sport"),
                STLVmWrFlowVar(fv_name="dport", pkt_offset="UDP.dport"),
                STLVmFixChecksumHw(
                    l3_offset="IP", l4_offset="UDP", l4_type=CTRexVmInsFixHwCs.L4_TYPE_UDP
                ),
            ]
        )

        return self._create_stl_stream(packet, vm)

    def is_dns4_query_rand_dst_port_stream_packet(self, packet):
        """Check that packet is part of
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.dns4_query_rand_dst_port_stream`.
        """

        pkt = Ether(packet["binary"])

        if IP in pkt and UDP in pkt:
            if self._ips_in_range(pkt["IP"].src, pkt["IP"].dst) and self._ports_in_range(
                pkt["UDP"].sport, pkt["UDP"].dport
            ):

                # DNS header must be parsed from Raw data, Scapy doesn't parse it if source or destination port isn't 53 or 5353
                if Raw in pkt:
                    try:
                        prev_level = logging.getLogger("scapy.runtime").getEffectiveLevel()
                        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
                        # Catch exception in case DNS() parsing fails
                        dns_hdr = DNS(pkt[Raw].load)
                    except Exception:
                        logging.getLogger("scapy.runtime").setLevel(prev_level)
                        return False

                    if DNS in dns_hdr and DNSQR in dns_hdr:
                        logging.getLogger("scapy.runtime").setLevel(prev_level)

                        if (
                            dns_hdr["DNS"].qd.qtype == 255
                            and dns_hdr["DNS"].qd.qname == b"trex-tgn.cisco.com."
                            and len(pkt)
                            == self._get_expected_packet_size(
                                self._create_frame()
                                / IP()
                                / UDP()
                                / DNS(qd=DNSQR(qname="trex-tgn.cisco.com"))
                            )
                        ):
                            return True

                    else:
                        logging.getLogger("scapy.runtime").setLevel(prev_level)
        return False
