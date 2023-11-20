"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Base TRex class implements common methods for
both stateless and advanced stateful TRexes.
"""

import os
import pathlib

import lbr_trex_client  # noqa: F401
import scapy.all as scapy
import yaml


class TRexZMQPortsUsedError(Exception):
    """Custom exception raised when TRex fails to start
    due to ZMQ ports being used by another process.
    """


class TRexBase:
    """Base TRex class.

    Class implements common methods for both stateless and
    advanced stateful modes of TRex.
    """

    def __init__(self):
        self._handler = None
        self._daemon = None
        self._ports = None

    def connect(self, request, generator, conf_file, force=False):
        """Connect to TRex.

        Execute following steps:
            1) Connect to TRex daemon.
                Daemon is launched when TRex machine is configured with Ansible playbook.
            2) Start TRex via daemon.
                Daemon can start and stop only one TRex instance.
            3) Acquire available physical ports of NIC.
                Which physical ports are available is set in configuration file.
            4) Return handler to connected TRex.

        Parameters
        ----------
        request : fixture
            Special pytest fixture, here used for finalizer.
        generator : TRexGenerator
            TRex generator object.
        conf_file : str
            Path to configuration file (on local machine).
        force : bool, optional
            If True, kill previous instance if it's running before starting TRex.

        Returns
        -------
        TRexBase
            Connected TRex.

        Raises
        ------
        TRexZMQPortsUsedError
            When TRex fails to start due to ZMQ ports
            being used by another process.
        """

        self._daemon = generator.get_daemon()
        # Assemble path to configuration file on TRex machine
        remote_cfg_file = pathlib.Path(
            self._daemon.get_trex_files_path(), os.path.basename(conf_file)
        )

        if force:
            self._daemon.force_kill(confirm=False)

        with open(conf_file, "r") as f:
            cfg = yaml.safe_load(f)

        try:
            self._handler = self._start_trex(
                generator.get_host(),
                remote_cfg_file,
                cfg[0]["zmq_rpc_port"],
                cfg[0]["zmq_pub_port"],
            )
        except Exception as err:
            # TRex can provide general Exception during startup failure.
            # It contains full startup log. If log contains certain
            # strings, raise custom exception.
            if (
                len(err.args) >= 1
                and isinstance(err.args[0], str)
                and (
                    "ZMQ: Address already in use" in err.args[0]
                    or "ZMQ port is used by the following process" in err.args[0]
                    or "unable to bind ZMQ server at" in err.args[0]
                )
            ):
                raise TRexZMQPortsUsedError(
                    f"ZMQ ports {cfg[0]['zmq_rpc_port']} or {cfg[0]['zmq_pub_port']} already used."
                )
            else:
                raise

        self._handler.connect()
        request.addfinalizer(self.terminate)

        # Acquire available ports and (re)initialize them
        self._handler.reset()
        self._ports = self._handler.get_acquired_ports()

        return self

    def terminate(self):
        """Terminate TRex.

        Disconnect from TRex, then terminate it via its daemon.
        """

        self._handler.disconnect()
        self._daemon.stop_trex()

    def _start_trex(self, host, remote_cfg_file, sync_port, async_port):
        """Start TRex and return its handler.

        Method is implemented in derived classes.
        """

        raise NotImplementedError()

    def _check_valid_port(self, port):
        """Check that provided port is a valid port."""

        assert port in self._ports, f"Port {port} is not in a list of valid ports ({self._ports})."

    def get_handler(self):
        """Get TRex handler that is used by official API.

        Official TRex API can be complicated for newcomers.
        Handler returned by ``connect`` provides simplified
        API that is easier to work with, but it lacks some
        advanced features of official API.

        Official documentation can be found at these links:
            https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/index.html
            https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/index.html

        Returns
        -------
        Union[ASTFClient, STLClient]
            Official TRex handler.
        """

        return self._handler

    def set_vlan(self, vlan, port=None):
        """Set VLAN.

        Parameters
        ----------
        vlan : int
            VLAN ID.
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        """

        if port is None:
            ports = self._ports
        else:
            self._check_valid_port(port)
            ports = [port]

        for port in ports:
            if port in self._handler.get_service_enabled_ports():
                self._handler.set_vlan(port, vlan)
            else:
                self._handler.set_service_mode(ports=port, enabled=True)
                self._handler.set_vlan(port, vlan)
                self._handler.set_service_mode(ports=port, enabled=False)

    def get_vlan(self, port=None):
        """Get currently configured VLAN.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, use first available port.

        Returns
        -------
        int
            VLAN ID.
        """

        if port is None:
            port = self._ports[0]

        self._check_valid_port(port)

        return self._handler.get_port_attr(port)["vlan"]

    def set_dst_mac(self, mac, port=None):
        """Set destination MAC address.

        Parameters
        ----------
        mac : str
            MAC address.
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        """

        if port is None:
            ports = self._ports
        else:
            self._check_valid_port(port)
            ports = [port]

        for port in ports:
            if port in self._handler.get_service_enabled_ports():
                self._handler.set_l2_mode(port, mac)
            else:
                self._handler.set_service_mode(ports=port, enabled=True)
                self._handler.set_l2_mode(port, mac)
                self._handler.set_service_mode(ports=port, enabled=False)

    def get_dst_mac(self, port=None):
        """Get destination MAC address.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, use first available port.

        Returns
        -------
        str
            MAC address.
        """

        if port is None:
            port = self._ports[0]

        self._check_valid_port(port)

        return self._handler.get_port_attr(port)["dest"]

    def get_src_mac(self, port=None):
        """Get source MAC address.

        Parameters
        ----------
        port : int, optional
            Port ID.
            If not set, use first available port.

        Returns
        -------
        str
            MAC address.
        """

        if port is None:
            port = self._ports[0]

        self._check_valid_port(port)

        return self._handler.get_port_attr(port)["src_mac"]

    def _preprocess_ports(self, port):
        """Validate ports and transform None value to all available ports."""

        if port is not None:
            self._check_valid_port(port)
        else:
            port = self._ports

        return port

    def start_capture(self, limit, port=None, bpf_filter=""):
        """Start capturing traffic (both RX and TX) on given port.

        This will significantly reduce performance
        as capturing is done in software.

        Parameters
        ----------
        limit : int
            Maximum number of packets to capture.
            Limited by available memory.
        port : int, optional
            Port ID.
            If not set, apply to all available ports.
        bpf_filter : str, optional
            Berkeley Packet Filter pattern. Only packets matching
            the filter will be appended to the capture.

        Returns
        -------
        dict
            Capture ID. It is required parameter for ``stop_capture``.

        Raises
        ------
        RuntimeError
            Packet capture is not enabled.
        """

        cid = self._handler.start_capture(
            tx_ports=port,
            rx_ports=port,
            limit=limit,
            mode="fixed",
        )["id"]

        return {"id": cid, "port": port}

    def stop_capture(self, capture_id, pcap_file=None):
        """Stop capture and provide captured traffic.

        Parameters
        ----------
        capture_id : dict
            Capture ID returned by ``start_capture``.
        pcap_file : str, optional
            If set, save traffic into given file in PCAP format.

        Returns
        -------
        None or list(scapy.layers.l2.Ether)
            List of packets in Scapy format.
            If ``pcap_file`` is provided, nothing is returned as
            traffic was saved into PCAP file instead.
        """

        if pcap_file is not None:
            self._handler.stop_capture(capture_id["id"], pcap_file)
            return None

        def _extract_packet_data(pkt):
            return scapy.Ether(pkt["binary"])

        packets = []
        self._handler.stop_capture(capture_id["id"], packets)

        return list(map(_extract_packet_data, packets))
