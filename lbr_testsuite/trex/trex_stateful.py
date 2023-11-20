"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Module implements Advanced Stateful TRex generator class.

In this mode, TRex implements full TCP/IP stack and
stores connection state. It can simulate realistic
traffic (e.g. HTTP browsing) that reacts to network
events, such as SYN packet being dropped by mitigation
device.
"""

import ipaddress
from dataclasses import dataclass
from typing import List, Tuple

import lbr_trex_client  # noqa: F401
import trex.astf.trex_astf_client as trex_astf_client
import trex.astf.trex_astf_profile as trex_astf_profile

from .trex_base import TRexBase


@dataclass(frozen=True)
class TRexProfile:
    """Class representing TRex profile.

    Strings in parameters are case-insensitive.

    Main component of profile is ``program``. It determines
    behaviour of client and server via set of commands. For
    example::

        Client                  Server

        connect()           accept()
        SYN------------------------>
        <--------------------SYN+ACK
        ACK------------------------>

        send()                recv()
        HTTP request--------------->
        recv()                send()
        <--------------HTTP response

        close()
        FIN+ACK-------------------->
        .                    close()
        <--------------------FIN+ACK
        ACK------------------------>

    Traffic is always generated between client and server.

    Parameters
    ----------
    program : tuple(trex_astf_profile.ASTFProgram, trex_astf_profile.ASTFProgram)
        Pair of programs determine behaviour of client and server.
        First element contains client program, second element
        contains server program.
        For details see:
        https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class
    client_net : str
        Client IP network, eg. '10.0.0.0/24'.
        IPv6 addresses must have prefix length in 96-128 range
        due to 32bit limitations in TRex engine.
    server_net : str
        Server IP network, eg. '10.0.1.0/26'.
        IPv6 addresses must have prefix length in 96-128 range
        due to 32bit limitations in TRex engine.
    conn_rate : int
        Rate of new connections per second.
    l4_dst : int, optional
        Destination port.
        Server listens for incoming connections on this port.
        Client generates traffic with this destination port.
    """

    program: Tuple[trex_astf_profile.ASTFProgram, trex_astf_profile.ASTFProgram]
    client_net: str
    server_net: str
    conn_rate: int
    l4_dst: int = 80

    def __post_init__(self):
        """Post-init check of parameters."""

        assert 0 <= self.l4_dst <= 65535, f"Invalid destination port ({self.l4_dst})"

        client_net = ipaddress.ip_network(self.client_net)
        server_net = ipaddress.ip_network(self.server_net)
        assert client_net.version == server_net.version, "Cannot mix IPv4 and IPv6"

        if client_net.version == 6:
            assert client_net.prefixlen >= 96, "Only prefix lengths 96-128 are supported."
            assert server_net.prefixlen >= 96, "Only prefix lengths 96-128 are supported."


@dataclass(frozen=True)
class TRexProfilePcap:
    """Class representing TRex profile for sending existing .pcap files.

    Strings in parameters are case-insensitive.

    Parameters
    ----------
    pcap_files : list(tuple(str, int))
        List of tuples that contain .pcap file to be
        loaded into profile and a speed at which to send .pcaps.
        Stated in connections per second.
    client_net : str
        Client IP network, eg. '10.0.0.0/24'.
        IPv6 addresses must have prefix length in 96-128 range
        due to 32bit limitations in TRex engine.
    server_net : str
        Server IP network, eg. '10.0.1.0/26'.
        IPv6 addresses must have prefix length in 96-128 range
        due to 32bit limitations in TRex engine.
    """

    pcap_files: List[Tuple[str, float]]
    client_net: str
    server_net: str

    def __post_init__(self):
        """Post-init check of parameters."""

        client_net = ipaddress.ip_network(self.client_net)
        server_net = ipaddress.ip_network(self.server_net)
        assert client_net.version == server_net.version, "Cannot mix IPv4 and IPv6"

        if client_net.version == 6:
            assert client_net.prefixlen >= 96, "Only prefix lengths 96-128 are supported."
            assert server_net.prefixlen >= 96, "Only prefix lengths 96-128 are supported."


class TRexAdvancedStateful(TRexBase):
    """Advanced Stateful TRex generator class.

    Attributes
    ----------
    _profile : TRexProfile or TRexProfilePcap
        TRex profile.
    """

    def __init__(self):
        super().__init__()
        self._profile = None

    def start(self, duration=-1):
        """Start generating traffic.

        Traffic generation is determined by profile
        (see ``TRexProfile`` or ``TRexProfilePcap``). It repeatedly creates new
        connections for given duration of time. Each new
        connection has different TCP sequence number,
        source port and possibly IP address (IP range is set in
        profile) just like real TCP traffic.

        Parameters
        ----------
        duration : float
            Duration in seconds.
            Default value (-1) means unlimited time.
        """

        self._handler.start(duration=duration)

    def stop(self):
        """Stop generating traffic."""

        self._handler.stop()

    def reset(self):
        """Reset TRex.

        Following steps are executed:
        1) stop any active traffic
        2) remove traffic profiles
        3) clear stats
        """

        self._handler.reset()
        self._profile = None

    def wait_on_traffic(self, timeout=None):
        """Wait until traffic generation finishes.

        Parameters
        ----------
        timeout : int, optional
            Timeout in seconds. Default value
            means no timeout.
        """

        self._handler.wait_on_traffic(timeout=timeout)

    def load_profile(self, profile):
        """Load profile.

        Parameters
        ----------
        profile : TRexProfile or TRexProfilePcap
            TRex profile.
        """

        assert self._profile is None, "Profile is already loaded"

        client_network = ipaddress.ip_network(profile.client_net)
        server_network = ipaddress.ip_network(profile.server_net)

        c_global_info = self._create_global_info(client_network)
        s_global_info = self._create_global_info(server_network)
        c_ip_range = self._create_ip_range(client_network)
        s_ip_range = self._create_ip_range(server_network)

        c_ip_dist = trex_astf_profile.ASTFIPGenDist(ip_range=c_ip_range, distribution="seq")
        s_ip_dist = trex_astf_profile.ASTFIPGenDist(ip_range=s_ip_range, distribution="seq")
        ip_gen = trex_astf_profile.ASTFIPGen(dist_client=c_ip_dist, dist_server=s_ip_dist)

        if isinstance(profile, TRexProfile):
            c_template = trex_astf_profile.ASTFTCPClientTemplate(
                program=profile.program[0],
                ip_gen=ip_gen,
                port=profile.l4_dst,
                cps=profile.conn_rate,
            )
            s_template = trex_astf_profile.ASTFTCPServerTemplate(
                program=profile.program[1],
                assoc=trex_astf_profile.ASTFAssociationRule(port=profile.l4_dst),
            )
            template = trex_astf_profile.ASTFTemplate(
                client_template=c_template, server_template=s_template
            )

            astf_profile = trex_astf_profile.ASTFProfile(
                default_ip_gen=ip_gen,
                templates=template,
                default_c_glob_info=c_global_info,
                default_s_glob_info=s_global_info,
            )

            self._handler.load_profile(astf_profile)
            self._profile = profile

        elif isinstance(profile, TRexProfilePcap):
            pcap_profile = trex_astf_profile.ASTFProfile(
                default_ip_gen=ip_gen,
                cap_list=[
                    trex_astf_profile.ASTFCapInfo(file=prf, cps=con_s)
                    for prf, con_s in profile.pcap_files
                ],
                default_c_glob_info=c_global_info,
                default_s_glob_info=s_global_info,
            )

            self._handler.load_profile(pcap_profile)
            self._profile = profile

    def get_profile(self):
        """Get loaded profile.

        Profile is read-only and cannot be modified.

        Returns
        -------
        TRexProfile or TRexProfilePcap or None
            TRex profile if it exists, None otherwise.
        """

        return self._profile

    def get_stats(self):
        """Get statistics.

        Apart from physical port statistics it also contains
        stateful (TCP) statistics for client and/or server.

        Example of statistics:

        {
            "global": {
                ...  # See TRexStateless.get_stats()
            },
            1: {
                ...
            },
            "total": {
                ...
            },
            "traffic": {
                "client": {
                    "m_active_flows": 0,
                    "m_est_flows": 0,
                    "m_tx_bw_l7_r": 0.0,
                    "m_tx_bw_l7_total_r": 0.0,
                    "m_rx_bw_l7_r": 0.0,
                    "m_tx_pps_r": 0.0,
                    "m_rx_pps_r": 0.0,
                    "m_avg_size": 0.0,
                    "m_tx_ratio": 0.0,
                    "-": 0,
                    "m_traffic_duration": 0,
                    "TCP": 0,
                    "tcps_connattempt": 0,
                    "tcps_accepts": 0,
                    "tcps_connects": 0,
                    "tcps_closed": 0,
                    "tcps_segstimed": 0,
                    "tcps_rttupdated": 0,
                    "tcps_delack": 0,
                    "tcps_sndtotal": 0,
                    "tcps_sndpack": 0,
                    "tcps_sndbyte": 0,
                    "tcps_sndbyte_ok": 0,
                    "tcps_sndctrl": 0,
                    "tcps_sndacks": 0,
                    "tcps_rcvtotal": 0,
                    "tcps_rcvpack": 0,
                    "tcps_rcvbyte": 0,
                    "tcps_rcvackpack": 0,
                    "tcps_rcvackbyte": 0,
                    "tcps_rcvackbyte_of": 0,
                    "tcps_preddat": 0,
                    "tcps_drops": 0,
                    "tcps_conndrops": 0,
                    "tcps_timeoutdrop": 0,
                    "tcps_rexmttimeo": 0,
                    "tcps_rexmttimeo_syn": 0,
                    "tcps_persisttimeo": 0,
                    "tcps_keeptimeo": 0,
                    "tcps_keepprobe": 0,
                    "tcps_keepdrops": 0,
                    "tcps_testdrops": 0,
                    "tcps_sndrexmitpack": 0,
                    "tcps_sndrexmitbyte": 0,
                    "tcps_sndprobe": 0,
                    "tcps_sndurg": 0,
                    "tcps_sndwinup": 0,
                    "tcps_rcvbadsum": 0,
                    "tcps_rcvbadoff": 0,
                    "tcps_rcvshort": 0,
                    "tcps_rcvduppack": 0,
                    "tcps_rcvdupbyte": 0,
                    "tcps_rcvpartduppack": 0,
                    "tcps_rcvpartdupbyte": 0,
                    "tcps_rcvoopackdrop": 0,
                    "tcps_rcvoobytesdrop": 0,
                    "tcps_rcvoopack": 0,
                    "tcps_rcvoobyte": 0,
                    "tcps_rcvpackafterwin": 0,
                    "tcps_rcvbyteafterwin": 0,
                    "tcps_rcvafterclose": 0,
                    "tcps_rcvwinprobe": 0,
                    "tcps_rcvdupack": 0,
                    "tcps_rcvacktoomuch": 0,
                    "tcps_rcvwinupd": 0,
                    "tcps_pawsdrop": 0,
                    "tcps_predack": 0,
                    "tcps_persistdrop": 0,
                    "tcps_badsyn": 0,
                    "tcps_reasalloc": 0,
                    "tcps_reasfree": 0,
                    "tcps_nombuf": 0,
                    "UDP": 0,
                    "udps_accepts": 0,
                    "udps_connects": 0,
                    "udps_closed": 0,
                    "udps_sndbyte": 0,
                    "udps_sndpkt": 0,
                    "udps_rcvbyte": 0,
                    "udps_rcvpkt": 0,
                    "udps_keepdrops": 0,
                    "udps_nombuf": 0,
                    "udps_pkt_toobig": 0,
                    "Flow Table": 0,
                    "err_cwf": 0,
                    "err_no_syn": 0,
                    "err_len_err": 0,
                    "err_fragments_ipv4_drop": 0,
                    "err_no_tcp_udp": 0,
                    "err_no_template": 0,
                    "err_no_memory": 0,
                    "err_dct": 0,
                    "err_l3_cs": 0,
                    "err_l4_cs": 0,
                    "err_redirect_rx": 0,
                    "redirect_rx_ok": 0,
                    "err_rx_throttled": 0,
                    "err_c_nf_throttled": 0,
                    "err_c_tuple_err": 0,
                    "err_s_nf_throttled": 0,
                    "err_flow_overflow": 0,
                    "defer_template": 0,
                    "err_defer_no_template": 0,
                },
                "server": {
                    ... # same as client
                },
            },
            "latency": {},
        }

        Returns
        ------
        dict
            Statistics.
        """

        return self._handler.get_stats(skip_zero=False)

    def start_capture(self, limit, port=None, bpf_filter=""):
        """Start capturing traffic (both RX and TX) on given port.

        Reimplementation of parent method. For details
        see TRexBase.start_capture.
        """

        port = self._preprocess_ports(port)

        return super().start_capture(limit, port, bpf_filter)

    def _start_trex(self, host, remote_cfg_file, sync_port, async_port):
        """Start TRex and return its handler.

        Implementation of abstract method from TRexBase.
        """

        self._daemon.start_astf(cfg=str(remote_cfg_file))

        return trex_astf_client.ASTFClient(
            server=host,
            sync_port=sync_port,
            async_port=async_port,
        )

    def _create_global_info(self, l3_network):
        """Create ASTF global info object based on IP version and network.

        For more information see table at
        https://trex-tgn.cisco.com/trex/doc/trex_astf.html#_tunables_reference_a_id_tunables_a
        """

        glob_info = trex_astf_profile.ASTFGlobalInfo()
        # Use dest. MAC from port configuration when sending reply
        glob_info.ip.dont_use_inbound_mac = 1

        if l3_network.version == 6:
            glob_info.ipv6.enable = 1
            glob_info.ipv6.src_msb = str(l3_network.network_address)
            glob_info.ipv6.dst_msb = str(l3_network.network_address)

        return glob_info

    def _create_ip_range(self, l3_network):
        """Create IP range from IP network.

        IP range is list of two items, where first item
        is first IP in range, and second item is last IP in range.
        """

        first_addr = l3_network.network_address
        last_addr = l3_network.broadcast_address

        if l3_network.version == 4:
            first_addr = str(ipaddress.IPv4Address(first_addr))
            last_addr = str(ipaddress.IPv4Address(last_addr))
        elif l3_network.version == 6:
            # TRex is limited by 32bit number generator.
            # Only lowest 32 bits of IPv6 can be modified.
            # Despite being IPv6, we must use IPv4 format
            # to set those 32 bits of address.
            first_addr = str(ipaddress.IPv4Address(first_addr.packed[12:16]))
            last_addr = str(ipaddress.IPv4Address(last_addr.packed[12:16]))

        return [first_addr, last_addr]
