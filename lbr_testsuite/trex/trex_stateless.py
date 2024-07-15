"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Module implements Stateless TRex generator class.

In this mode, TRex does not store any connection state.
It does not react to current situation on a network.
It is essentially a packet generator similar to Scapy or Spirent.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from typing import Optional, Union

import lbr_trex_client  # noqa: F401
import trex.stl.trex_stl_client as trex_stl_client
import trex.stl.trex_stl_packet_builder_scapy as trex_packet_builder
import trex.stl.trex_stl_streams as trex_stl_streams
from trex.utils.parsing_opts import decode_multiplier

from ..packet_crafter.random_types import RandomIP
from ..packet_crafter.trex_packet_crafter import TRexPacketCrafter
from .trex_base import TRexBase


_EMPTY_VLAN = "-"


class TRexStreamModeSelector(Enum):
    """Stream mode selector.

    Two modes are supported:

    - Continuous stream (generate traffic until stopped).
    - Burst stream (generate exact number of packets, then stop).
    """

    CONTINUOUS = 1
    BURST = 2


class TRexL4Flag(Enum):
    """Enum for tcp flag selection"""

    SYN = "S"
    ACK = "A"
    RST = "R"
    URG = "U"
    PSH = "P"
    FIN = "F"
    ECE = "E"
    CWR = "C"


@dataclass(frozen=True)
class TRexStream:
    """Class representing TRex stream.

    Strings in parameters are case-insensitive.

    L2 data are required to send a packet on an Ethernet network.
    If not set, default values are taken from port configuration.
    L3 and L4 data are optional. If not set, packet won't contain
    these layers.

    Parameters
    ----------
    port : int, optional
        Port ID.
        Stream is generated from this port.

    vlan_id : int, optional
        VLAN ID.
        If not set, VLAN ID from port configuration is used.
    l2_dst : str, optional
        Destination MAC address.
        If not set, address from port configuration is used.
    l2_src : str, optional
        Source MAC address.
        If not set, address from port configuration is used.

    l3 : str, optional
        L3 protocol. Supported types:
            | IPv4
            | IPv6
            | ARP (only for IPv4)
    l3_src : various, optional
        Source IP addresses. Examples of supported formats:
            | Single host: 10.0.0.0
            | Network: 2001:db8::/120
            | Set: {first='10.0.0.0', count=150, step=1}
            | Random addresses
            | Formats from ``ipaddresses`` module
            | List of previous formats
        For more details see  ``packet_crafter.ipaddresses`` module.
    l3_dst : various, optional
        Destination IP addresses. It has same format as ``l3_src``.

    l4 : str, optional
        L4 protocol. Supported types:
            | UDP
            | TCP
            | ICMP
            | SCTP
            | IGMP
            | NDP (only for IPv6)
    l4_src : various, optional
        Source ports. Supported formats:
            | Single port: 80
            | Range (min/max is included): (200, 1000)
            | List: [80, 443, 8080]
    l4_dst : various, optional
        Destination ports. It has same format as ``l4_src``.
    l4_op : str, optional
        Modifier of L4 values (both src and dst). Possible options:
        - "inc" for incrementing distribution (default).
        - "dec" for decrementing distribution.
        - "random" for random distribution.
    l4_flags : various, optional
        Any combination of TCP flags. Default value/flag is SYN.

    pkt_len : int, optional
        Packet length including Ethernet FCS field.

    rate : str, optional
        Rate of traffic.
        Can be set in packets per second, bits per second
        or percentage of max line throughput.
        Bits are defined on L1, which includes preamble
        and IPG (Interpacket gap). Examples:
            | 100%, 66.67%, 0.988 %
            | 100Gbps, 150Mbps, 1kbps, 800bps
            | 0.1Gpps, 120Mpps, 7kpps, 300pps

    mode_selector : TRexStreamModeSelector, optional
        Stream mode selector.
    burst_size : int, optional
        Total number of packets to send.
        Valid only if ``mode_selector`` is TRexStreamModeSelector.BURST.

    flow_stats_id : int, optional
        Packet Group ID for flow statistics of this stream.
        Can be any 32-bit number.
        Enabling flow stats significantly decreases throughput.

    disable_vm : bool, optional
        If True, do not apply any Field Engine instructions.
        This removes ability to set more than one L3/L4
        source/destination, but it can increase throughput.
    enabled : bool, optional
        If False, stream won't be transmited.
    """

    port: int = 0
    vlan_id: Optional[int] = None
    l2_dst: Optional[str] = None
    l2_src: Optional[str] = None
    l3: Optional[str] = None
    l3_src: Optional[Union[str, dict, list, RandomIP, IPv4Address, IPv6Address]] = None
    l3_dst: Optional[Union[str, dict, list, RandomIP, IPv4Address, IPv6Address]] = None
    l4: Optional[str] = None
    l4_src: Optional[Union[int, tuple, list]] = None
    l4_dst: Optional[Union[int, tuple, list]] = None
    l4_op: Optional[str] = "inc"
    l4_flags: Optional[Union[list, TRexL4Flag]] = TRexL4Flag.SYN
    pkt_len: int = 100
    rate: str = "1kpps"
    mode_selector: TRexStreamModeSelector = TRexStreamModeSelector.CONTINUOUS
    burst_size: Optional[int] = None
    flow_stats_id: Optional[int] = None
    disable_vm: bool = False
    enabled: bool = True

    def __post_init__(self):
        """Post-init check of parameters."""

        if self.l3 is not None:
            object.__setattr__(self, "l3", self.l3.lower())
            assert self.l3 in ("ipv4", "ipv6", "arp"), f"Bad L3 protocol ({self.l3})"

        if self.l4 is not None:
            object.__setattr__(self, "l4", self.l4.lower())
            assert self.l4 in (
                "tcp",
                "udp",
                "sctp",
                "igmp",
                "icmp",
                "ndp",
            ), f"Bad L4 protocol ({self.l4})"

        if self.pkt_len is not None:
            assert 64 <= self.pkt_len <= 1526, "Packet length must be between 64-1526 bytes."

        if self.rate is not None:
            object.__setattr__(self, "rate", self.rate.lower())


class TRexStateless(TRexBase):
    """Stateless TRex generator class.

    Attributes
    ----------
    _streams : list(TRexStream)
        List of streams.
    """

    def __init__(self):
        super().__init__()
        self._streams = []

    def start(self, port=None, duration=-1):
        """Start generating traffic.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        duration : float, optional
            Duration in seconds.
            Default value (-1) means unlimited time.
        """

        if port is not None:
            self._check_valid_port(port)

        self._handler.start(ports=port, duration=duration, force=True)

    def stop(self, port=None):
        """Stop generating traffic.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        """

        if port is not None:
            self._check_valid_port(port)

        self._handler.stop(ports=port)

    def reset(self, port=None):
        """Reset TRex port.

        Following steps are executed:
        1) stop any active traffic
        2) remove streams
        3) clear stats

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        """

        if port is not None:
            self._check_valid_port(port)

        self._handler.reset(ports=port)

    def wait_on_traffic(self, port=None, timeout=None):
        """Wait until traffic generation finishes.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        timeout : int, optional
            Timeout in seconds. Default value
            means no timeout.

        Raises
        ------
        TRexTimeoutError
            In case timeout has expired.
        """

        if port is not None:
            self._check_valid_port(port)

        self._handler.wait_on_traffic(ports=port, timeout=timeout)

    def add_stream(self, stream):
        """Add stream.

        Parameters
        ----------
        stream : TRexStream
            TRex Stream.
        """

        virtual_machine = None
        flow_stats = None
        spec = {key: val for key, val in asdict(stream).items() if val is not None}

        # 4B FCS is automatically added by NIC
        spec["pkt_len"] -= 4

        if "vlan_id" not in spec:
            if self.get_vlan(stream.port) != _EMPTY_VLAN:
                spec["vlan_id"] = self.get_vlan(stream.port)

        packet, fe_instructions = TRexPacketCrafter().packet_with_fe_instructions(spec)

        if stream.flow_stats_id is not None:
            flow_stats = trex_stl_streams.STLFlowStats(pg_id=stream.flow_stats_id)

        if stream.disable_vm is False:
            virtual_machine = trex_packet_builder.STLScVmRaw(fe_instructions)

        stream_mode = self._create_stream_mode(
            stream.rate,
            stream.mode_selector,
            stream.burst_size,
        )

        stl_stream = trex_stl_streams.STLStream(
            packet=trex_packet_builder.STLPktBuilder(pkt=packet, vm=virtual_machine),
            mode=stream_mode,
            flow_stats=flow_stats,
            enabled=stream.enabled,
        )

        self._handler.add_streams(stl_stream, ports=stream.port)
        self._streams.append(stream)

    def get_streams(self):
        """Get list of added streams.

        Streams are read-only and cannot be modified.

        Returns
        ------
        list(TRexStream)
            List of streams.
        """

        return self._streams

    def get_stats(self, port=None):
        """Get statistics for given port.

        Example of statistics:

            {
                "global": {
                    "active_flows": 0.0,
                    "active_sockets": 0,
                    "bw_per_core": 14.64527702331543,
                    "cpu_util": 0.45707881450653076,
                    "cpu_util_raw": 0.1666666716337204,
                    "open_flows": 0.0,
                    "platform_factor": 1.0,
                    "rx_bps": 229422096.0,
                    "rx_core_pps": 131572.71875,
                    "rx_cpu_util": 5.748239040374756,
                    "rx_drop_bps": 373042016.0,
                    "rx_pps": 131592.703125,
                    "socket_util": 0.0,
                    "tx_expected_bps": 0.0,
                    "tx_expected_cps": 0.0,
                    "tx_expected_pps": 0.0,
                    "tx_pps": 597417.9375,
                    "tx_bps": 602464128.0,
                    "tx_cps": 0.0,
                    "total_servers": 0,
                    "total_clients": 0,
                    "total_alloc_error": 0,
                    "queue_full": 0,
                },
                0: {  # Port ID 0
                    "opackets": 4000000,
                    "ipackets": 2,
                    "obytes": 400000000,
                    "ibytes": 156,
                    "oerrors": 0,
                    "ierrors": 0,
                    "tx_bps": 398414112.0,
                    "tx_pps": 498017.625,
                    "tx_bps_L1": 478096932.0,
                    "tx_util": 0.478096932,
                    "rx_bps": 1.7691899538040161,
                    "rx_pps": 0.002835240215063095,
                    "rx_bps_L1": 2.2228283882141118,
                    "rx_util": 2.2228283882141116e-09,
                },
                1: {...},  # Port ID 1
                2: {...},  # Port ID 2
                "total": {...},  # Sum from all ports
                "flow_stats": {
                    "global": {"rx_err": {0: 0, 1: 0, 2: 0}, "tx_err": {0: 0, 1: 0, 2: 0}},
                    1: {  # Stream flow stats ID 1

                        # Stats for ports ID 0, 1, 2
                        "rx_pkts": {0: 0, 1: 0, 2: 797765, "total": 797765},
                        "rx_bytes": {0: 0, 1: 0, 2: 204227840, "total": 204227840},
                        "tx_pkts": {0: 0, 1: 799299, 2: 0, "total": 799299},
                        "tx_bytes": {0: 0, 1: 204620544, 2: 0, "total": 204620544},
                        "rx_bps": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                        "rx_pps": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                        "tx_bps": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                        "tx_pps": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                        "rx_bps_l1": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                        "tx_bps_l1": {0: 0.0, 1: 0.0, 2: 0.0, "total": 0.0},
                    },
                    2: {...},  # Stream flow stats ID 2
                    3: {...},  # Stream flow stats ID 3
                },
                "latency": {"global": {"old_flow": 0, "bad_hdr": 0}},
            }


        Parameters
        ----------
        port : int, optional
            Port ID. If None, get statistics from all ports.

        Returns
        ------
        dict
            Port statistics.
        """

        if port is not None:
            self._check_valid_port(port)

        return self._handler.get_stats(ports=port)

    def start_capture(self, limit, port=None, bpf_filter=""):
        """Start capturing traffic (both RX and TX) on given port.

        Reimplementation of parent method. For details
        see TRexBase.start_capture.
        """

        port = self._preprocess_ports(port)
        self._handler.set_service_mode(ports=port, enabled=True)

        return super().start_capture(limit, port, bpf_filter)

    def stop_capture(self, capture_id, pcap_file=None):
        """Stop capture and provide captured traffic.

        Reimplementation of parent method. For details
        see TRexBase.stop_capture.
        """

        ret = super().stop_capture(capture_id, pcap_file)
        self._handler.set_service_mode(ports=capture_id["port"], enabled=False)

        return ret

    def _start_trex(self, host, remote_cfg_file, sync_port, async_port):
        """Start TRex and return its handler.

        Implementation of abstract method from TRexBase.
        """

        self._daemon.start_stateless(cfg=str(remote_cfg_file))

        return trex_stl_client.STLClient(
            server=host,
            sync_port=sync_port,
            async_port=async_port,
        )

    def _bandwidth_param(self, rate):
        """Get bandwidth parameters."""

        rate = rate.lower()
        rate = rate.replace(" ", "")
        value = decode_multiplier(rate)["value"]

        if rate[-1] == "%":
            return dict(percentage=value)
        elif rate[-3:] == "pps":
            return dict(pps=value)
        elif rate[-3:] == "bps":
            return dict(bps_L1=value)
        else:
            assert False, f"Rate units must end with either '%', 'pps' or 'bps' (got {rate})."

    def _create_stream_mode(self, rate, mode_selector, total_pkts=None):
        """Create "stream mode" object.

        Object contains information about traffic generation speed and count.

        Parameters
        ----------
        rate : str
            Traffic rate.
        mode_selector : TRexStreamModeSelector
            Stream mode selector.
        total_pkts : int, optional
            Number of packets to generate.
            Valid only if ``mode_selector`` is TRexStreamModeSelector.BURST.
        """

        params = self._bandwidth_param(rate)

        if mode_selector is TRexStreamModeSelector.CONTINUOUS:
            mode = trex_stl_streams.STLTXCont(**params)
        elif mode_selector is TRexStreamModeSelector.BURST:
            mode = trex_stl_streams.STLTXSingleBurst(**params, total_pkts=total_pkts)

        return mode
