"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET

Class containing definition of commonly used
TRex stateful traffic profiles.
"""


import lbr_trex_client.paths  # noqa: F401

from trex.astf.api import *


class TRex_Astf_Profile_Generator():
    """Class containing definition of commonly used traffic profiles.

    Profiles can be costumized according to input arguments.
    Only parameters for commonly used use cases were selected.
    What is currently NOT supported is per-template "info" (eg.
    concurrent IPv4/IPv6 traffic or multiple traffic
    programs (= templates, hence per-template)).
    Global info (gi) parameters are currently used for both
    client and server side.

    TRex supports more customization and class can be extended
    if new requirements appear. Some TRex documentation can be found
    `here <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html>`_.

    Example of intended class usage::

        traffic_profile = TRex_Astf_Profile_Generator(server_port=443, cps=1000, gi_tcp_txbufsize=1024)
        traffic_trex.load_profile(traffic_profile.http6_profile())

    Parameters
    ----------
    client_ipv4_from : str, optional
        IPv4 source address - beginning of range.
    client_ipv4_to : str, optional
        IPv4 source address - end of range. Exact number of
        IP addresses is the **multiple of CPU cores** (defined by
        TRex config file), always equal or lower than defined range.
    client_ipv4_op : str, optional
        IPv4 source address - distribution (``rand, seq``).
    server_ipv4_from : str, optional
        IPv4 destination address - beginning of range.
    server_ipv4_to : str, optional
        IPv4 destination address - end of range. Exact number of
        IP addresses is the **multiple of CPU cores** (defined by
        TRex config file), always equal or lower than defined range.
    server_ipv4_op : str, optional
        IPv4 destination address - distribution (``rand, seq``).

    ipv6_msb : str, optional
        MSB (96 bits) of IPv6 address. ASTF TRex can change only
        lowest 32 bits of IPv6 address. See
        :meth:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator.udp6_stream`
        for example of setting IPv6 range correctly.
    client_ipv6_from : str, optional
        IPv6 source address (lowest 32 bits) - beginning of range.
        Use IPv4 notation.
    client_ipv6_to : str, optional
        IPv6 source address (lowest 32 bits) - end of range.
        Exact number of IP addresses is the **multiple of CPU cores**
        (defined by TRex config file), always equal or lower
        than defined range.
        Use IPv4 notation.
    client_ipv6_op : str, optional
        IPv6 source address - distribution (``rand, seq``).
    server_ipv6_from : str, optional
        IPv6 destination address (lowest 32 bits) - beginning of range.
        Use IPv4 notation.
    server_ipv6_to : str, optional
        IPv6 destination address (lowest 32 bits) - end of range.
        Exact number of IP addresses is the **multiple of CPU cores**
        (defined by TRex config file), always equal or lower
        than defined range.
        Use IPv4 notation.
    server_ipv6_op : str, optional
        IPv6 destination address - distribution (``rand, seq``).

    server_port : int, optional
        Server port.
    cps : int, optional
        Generate N connections per second between client and server.

    gi_ip_dont_use_inbound_mac : int, optional
        Only for server. If 0, use source MAC address as destination
        MAC address for reply. Otherwise use destination MAC from
        configuration file (if defined) or resolved gateway MAC.
    gi_tcp_rxbufsize : int, optional
        Socket RX buffer size in bytes. Allowed value is between
        1024-1048576. Used for both client and server.
    gi_tcp_txbufsize : int, optional
        Socket TX buffer size in bytes. Allowed value is between
        1024-1048576. Used for both client and server.
    gi_tcp_blackhole: int, optional
        Allowed values are 0 (return RST packet in case of error),
        1 (return of RST only in SYN) or
        2 (don’t return any RST packet, make a blackhole).
        Used for both client and server.
    gi_tcp_keepinit: int, optional
        Value in second for TCP keepalive. Possible values are 2-65533.
        Used for both client and server.
    gi_tcp_keepidle: int, optional
        Value in second for TCP keepidle. Possible values are 2-65533.
        Used for both client and server.
    gi_tcp_keepintvl: int, optional
        Value in second for TCP keepalive interval.
        Possible values are 2-65533. Used for both client and server.
    """

    def __init__(
        self,
        client_ipv4_from='10.0.0.1',
        client_ipv4_to='10.0.0.254',
        client_ipv4_op='rand',
        server_ipv4_from='10.0.1.1',
        server_ipv4_to='10.0.1.62',
        server_ipv4_op='rand',

        ipv6_msb='2001:db8::',
        client_ipv6_from='0.0.0.1',
        client_ipv6_to='0.0.0.254',
        client_ipv6_op='rand',
        server_ipv6_from='0.0.1.1',
        server_ipv6_to='0.0.1.62',
        server_ipv6_op='rand',

        server_port=80,
        cps=1,

        gi_ip_dont_use_inbound_mac=0,
        gi_tcp_rxbufsize=32768,
        gi_tcp_txbufsize=32768,
        gi_tcp_blackhole=0,
        gi_tcp_keepinit=10,
        gi_tcp_keepidle=10,
        gi_tcp_keepintvl=10
    ):

        # Define all parameters as class attributes
        for param, value in locals().items():
            if param != 'self':
                setattr(self, param, value)

        # Taken from TRex docs to have somewhat realistic HTTP request/response
        self.http_req = (
            b'GET /3384 HTTP/1.1\r\nHost: 22.0.0.3\r\nConnection: Keep-Alive\r\nUser-Agent: Mozilla/4.0' +
            b'(compatible; MSIE 7.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)\r\nAccept: */*\r\n' +
            b'Accept-Language: en-us\r\nAccept-Encoding: gzip, deflate, compress\r\n\r\n'
        )
        self.http_response = (
            'HTTP/1.1 200 OK\r\nServer: Microsoft-IIS/6.0\r\nContent-Type: text/html\r\nContent-Length: ' +
            '32000\r\n\r\n<html><pre>**********</pre></html>'
        )

        self.udp_req = 128 * 'x'
        self.udp_response = 256 * 'x'

    def _create_global_info(self, server_side=False, ipv6=False):
        glob_info = ASTFGlobalInfo()
        glob_info.tcp.rxbufsize = self.gi_tcp_rxbufsize
        glob_info.tcp.txbufsize = self.gi_tcp_txbufsize
        glob_info.tcp.blackhole = self.gi_tcp_blackhole
        glob_info.tcp.keepinit = self.gi_tcp_keepinit
        glob_info.tcp.keepidle = self.gi_tcp_keepidle
        glob_info.tcp.keepintvl = self.gi_tcp_keepintvl

        if server_side:
            glob_info.ip.dont_use_inbound_mac = self.gi_ip_dont_use_inbound_mac
        if ipv6:
            glob_info.ipv6.src_msb = self.ipv6_msb
            glob_info.ipv6.dst_msb = self.ipv6_msb
            glob_info.ipv6.enable = 1

        return glob_info

    def _create_profile(self, prog_c, prog_s, c_glob_info, s_glob_info, ipv6=False):
        if ipv6:
            ip_gen_c = ASTFIPGenDist(ip_range=[self.client_ipv6_from, self.client_ipv6_to], distribution=self.client_ipv6_op)
            ip_gen_s = ASTFIPGenDist(ip_range=[self.server_ipv6_from, self.server_ipv6_to], distribution=self.server_ipv6_op)
            ip_gen = ASTFIPGen(glob=ASTFIPGenGlobal(ip_offset="1.0.0.0"), dist_client=ip_gen_c, dist_server=ip_gen_s)
        else:
            ip_gen_c = ASTFIPGenDist(ip_range=[self.client_ipv4_from, self.client_ipv4_to], distribution=self.client_ipv4_op)
            ip_gen_s = ASTFIPGenDist(ip_range=[self.server_ipv4_from, self.server_ipv4_to], distribution=self.server_ipv4_op)
            ip_gen = ASTFIPGen(glob=ASTFIPGenGlobal(ip_offset="1.0.0.0"), dist_client=ip_gen_c, dist_server=ip_gen_s)

        temp_c = ASTFTCPClientTemplate(program=prog_c, ip_gen=ip_gen, port=self.server_port, cps=self.cps)
        temp_s = ASTFTCPServerTemplate(program=prog_s, assoc=ASTFAssociationRule(port=self.server_port))
        template = ASTFTemplate(client_template=temp_c, server_template=temp_s)

        return ASTFProfile(
            default_ip_gen=ip_gen,
            templates=template,
            default_c_glob_info=c_glob_info,
            default_s_glob_info=s_glob_info
        )

    def _profile(self, prog_c, prog_s, ipv6=False):
        if ipv6:
            c_glob_info = self._create_global_info(ipv6=True)
            s_glob_info = self._create_global_info(server_side=True, ipv6=True)
            return self._create_profile(prog_c, prog_s, c_glob_info, s_glob_info, ipv6=True)
        else:
            c_glob_info = self._create_global_info()
            s_glob_info = self._create_global_info(server_side=True)
            return self._create_profile(prog_c, prog_s, c_glob_info, s_glob_info)

    def http4_profile(self):
        """Create simple IPv4/TCP/HTTP traffic profile using manual
        `ASTFProgram <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class>`_ commands.

        Each connection should look like this::

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

        Returns
        -------
        ASTFProfile
            TRex profile.
        """

        # Client
        prog_c = ASTFProgram(side='c')
        prog_c.connect()    # Establish TCP connection
        prog_c.send(self.http_req)
        prog_c.recv(len(self.http_response))
        # Implicit TCP close()

        # Server
        prog_s = ASTFProgram(side='s')
        prog_s.accept()    # Wait for TCP connection
        prog_s.recv(len(self.http_req))
        prog_s.send(self.http_response)

        return self._profile(prog_c, prog_s)

    def http6_profile(self):
        """Create simple IPv6/TCP/HTTP traffic profile using manual
        `ASTFProgram <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class>`_ commands.

        Returns
        -------
        ASTFProfile
            TRex profile.
        """

        prog_c = ASTFProgram(side='c')
        prog_c.connect()
        prog_c.send(self.http_req)
        prog_c.recv(len(self.http_response))

        prog_s = ASTFProgram(side='s')
        prog_s.accept()
        prog_s.recv(len(self.http_req))
        prog_s.send(self.http_response)

        return self._profile(prog_c, prog_s, ipv6=True)

    def udp4_profile(self):
        """Create simple IPv4/UDP/L7 traffic profile using manual
        `ASTFProgram <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class>`_ commands.

        Returns
        -------
        ASTFProfile
            TRex profile.
        """

        prog_c = ASTFProgram(side='c', stream=False)
        prog_c.send_msg(self.udp_req)
        prog_c.recv_msg(1)    # Receive 1 packet

        prog_s = ASTFProgram(side='s', stream=False)
        prog_s.recv_msg(1)
        prog_s.send_msg(self.udp_response)

        return self._profile(prog_c, prog_s)

    def udp6_profile(self):
        """Create simple IPv6/UDP/L7 traffic profile using manual
        `ASTFProgram <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class>`_ commands.

        Returns
        -------
        ASTFProfile
            TRex profile.
        """

        prog_c = ASTFProgram(side='c', stream=False)
        prog_c.send_msg(self.udp_req)
        prog_c.recv_msg(1)

        prog_s = ASTFProgram(side='s', stream=False)
        prog_s.recv_msg(1)
        prog_s.send_msg(self.udp_response)

        return self._profile(prog_c, prog_s, ipv6=True)

    def simple_pcap_profile(self, pcap_file, ipv6=False):
        """Create traffic profile using supplied PCAP file.

        Only IPv4/IPv6 (based on 'ipv6' parameter) and 'cps' class
        attributes are used. Rest is based on PCAP file.

        Parameters
        ----------
        pcap_file : str
            Path to PCAP file.
        ipv6 : bool, optional
            If True, use IPv6 range. Otherwise use IPv4 range.

        Returns
        -------
        ASTFProfile
            TRex profile.
        """

        if ipv6:
            ip_gen_c = ASTFIPGenDist(ip_range=[self.client_ipv6_from, self.client_ipv6_to], distribution=self.client_ipv6_op)
            ip_gen_s = ASTFIPGenDist(ip_range=[self.server_ipv6_from, self.server_ipv6_to], distribution=self.server_ipv6_op)
            ip_gen = ASTFIPGen(glob=ASTFIPGenGlobal(ip_offset="1.0.0.0"), dist_client=ip_gen_c, dist_server=ip_gen_s)
        else:
            ip_gen_c = ASTFIPGenDist(ip_range=[self.client_ipv4_from, self.client_ipv4_to], distribution=self.client_ipv4_op)
            ip_gen_s = ASTFIPGenDist(ip_range=[self.server_ipv4_from, self.server_ipv4_to], distribution=self.server_ipv4_op)
            ip_gen = ASTFIPGen(glob=ASTFIPGenGlobal(ip_offset="1.0.0.0"), dist_client=ip_gen_c, dist_server=ip_gen_s)

        return ASTFProfile(default_ip_gen=ip_gen, cap_list=[ASTFCapInfo(file=pcap_file, cps=self.cps)])
