"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020 CESNET, z.s.p.o.

Spirent class for tests using STC for traffic generation. This class:
- provides initialization of Spirent Test Center (STC) handler for STC
control,
- handles connection to STC terminal server and spirent chassis on given
port,
- provides STC control methods.

Connection and control of STC is realized via spirentlib library and
server application. "Spirentlib server" listens on a specific port on
a server where STC is installed.

To start using STC follow these steps:
1) Create and initialize an instance of Spirent class.
2) Connect to the spirentlib server.
3) If non-default STC configuration should be used, set path to a
configuration file.
4) Load the configuration and connect to chassis port.

After these steps you can start using STC for packet generation.
When you finish your work, disconnection from spirent chassis is
required. Otherwise spirent chassis port stay reserved and cannot be
used until it is unbound manually.
"""

import logging
import time

from ..common import wait_until_condition
from ..topology.generator import Generator
from .spirentlib.spirentlib import STC_API_OFFICIAL, STC_API_PROPRIETARY, StcHandler


STC_API_PROPRIETARY = STC_API_PROPRIETARY
STC_API_OFFICIAL = STC_API_OFFICIAL


class Spirent(Generator):
    """Base spirent test class extending BaseTest class.

    Attributes
    ----------
    _DEFAULT_SERVER_PORT : int
        Server port for connection to the spirent test center.
    _stc_handler : :class:`StcHandler`
        Handler for communication with Spirent Test Center (STC).
    _spirent_config : str
        Path to STC configuration.
    _server : str
        Address of Spirent Test Center server.
    _chassis : str
        Address of Spirent Test Center chassis.
    _port : str
        Spirent Test Center chassis port.
    _port_reserved : bool
        Flag whether a spirent chassis port is reserved.
    _logger : logging.Logger
        Logger for outputs.
    """

    """Server part of STC API which converts commands from Python API
    to TCL API listens on this port number."""
    _DEFAULT_SERVER_PORT = dict()
    _DEFAULT_SERVER_PORT[STC_API_OFFICIAL] = 8888
    _DEFAULT_SERVER_PORT[STC_API_PROPRIETARY] = 42000

    def __init__(
        self,
        server,
        chassis,
        port,
        api_version=STC_API_OFFICIAL,
        api_session_start_timeout=120,
        server_port=None,
        force_port_reservation=False,
        link_wait_timeout=60.0,
    ):
        """
        Parameters
        ----------
        server : str
            Address of Spirent Test Center server.
        chassis : str
            Address of Spirent Test Center chassis.
        port : str
            Spirent Test Center chassis port.
        api_version : int
            spirentlib.STC_API_OFFICIAL for official spirent api or
            spirentlib.STC_API_PROPRIETARY for our proprietary api.
        server_port : int, optional
            Server port for connection to the spirent test center. If
            not set, the default port for given API version is used.
        force_port_reservation : bool
            Flag whether reservation of spirent chassis port should be
            forced or not (i.e. terminating any current reservation).
        link_wait_timeout : float, optional
            Timeout of waiting for link up before generating traffic.
        """

        self._server = server
        self._chassis = chassis
        self._port = port
        self._spirent_config = None
        self._logger = logging.getLogger(__name__)
        if server_port is None:
            self._server_port = Spirent._DEFAULT_SERVER_PORT[api_version]
        else:
            self._server_port = server_port
        self._stc_handler = StcHandler(api_version, api_session_start_timeout)
        self._port_reserved = False
        self._force_port_reservation = force_port_reservation
        self._link_wait_timeout = link_wait_timeout

    def set_config_file(self, config_path):
        """Configure STC configuration file.

        Parameters
        ----------
        config_path : str or pathlib.Path
            Path to the configuration file.
        """

        self._spirent_config = str(config_path)

    def get_port(self):
        """Spirent port getter.

        Returns
        -------
        str
            Spirent port.
        """

        return self._port

    def connect(self):
        """Establishes a connection to spirentlib server application."""

        self._logger.debug(
            f"Connecting to STC terminal server: {self._server}:{self._server_port}."
        )
        self._stc_handler.stc_api_connect(self._server, self._server_port)

    def _load_config(self):
        """Configure STC using the configuration file."""

        assert not self._port_reserved
        assert self._spirent_config, "Configuration file not set. Use set_config_file() to set it."

        self._logger.debug(f"Loading STC configuration: {self._spirent_config}.")
        self._stc_handler.stc_init(self._spirent_config)

    def _connect_chassis_port(self):
        """Connect to spirent chassis and reserve port.

        After this method is called, _load_config() should not be called
        until the port is unbound. Loading of a configuration would
        overwrite selected port by a port which is saved in the
        configuration.
        """

        self._logger.debug(f"Reserving STC port: {self._port} at chassis {self._chassis}.")
        self._stc_handler.stc_connect(self._chassis, self._port, self._force_port_reservation)

        self._port_reserved = True

    def load_config_and_connect_chassis_port(self):
        """Handle STC configuration and chassis setup.

        Note: This method exists as these steps needs to be executed in
        the given order.
        """

        self._load_config()
        self._connect_chassis_port()

    def disconnect_chassis(self):
        """Disconnect from spirent chassis and unbound spirent port."""

        self._logger.debug("Disconnecting from Spirent Test Center chassis.")
        self._stc_handler.stc_disconnect()

        self._port_reserved = False

    def set_result_view_mode(self, mode):
        """Set view mode of results.

        This affects which counters will be available in results.

        Parameters
        ----------
        mode : str
            Results view mode. For more information in modes see Spirent
            TestCenter Automation Programmer's Reference.
        """

        self._stc_handler.stc_set_result_view_mode(mode)

    def determine_src_mac_address(self):
        """Determine packets' source MAC address
        according to the used spirent port.

        This method is useful whenever there are more spirent generators running
        at the same time. These may use the same source MAC address for their
        stream blocks. In that case, the connected switch may infer the MAC
        address for one of the ports and then discard all packets coming from
        another port with the same source MAC address.

        Returns
        -------
        str
            MAC address corresponding to the spirent port.
        """

        mac_addr_template = "00:10:94:00:{0:02X}:{1:02X}"
        port_str = self.get_port().split("/")
        slot = int(port_str[0])
        port = int(port_str[1])

        return mac_addr_template.format(slot, port)

    @staticmethod
    def _object_name_list(obj_names):
        if isinstance(obj_names, str):
            obj_names = [obj_names]

        if not isinstance(obj_names, list):
            err_msg = (
                f'Object names must be defined as a list of strings but passed "{type(obj_names)}".'
            )
            raise TypeError(err_msg)

        return obj_names

    @staticmethod
    def _stream_blocks_presence_check(sb_handler, sb_names):
        if len(sb_handler) != len(sb_names):
            err_msg = (
                f'Some of defined stream blocks "{sb_names}" are not defined in STC configuration.'
            )
            raise ValueError(err_msg)

        for index, sb in enumerate(sb_handler):
            if len(sb) != 1:
                err_msg = f'Stream block "{sb_names[index]}" is not defined  in STC configuration!'
                raise ValueError(err_msg)

    def _stream_blocks_handler(self, stream_block_names):
        stream_block_names = self._object_name_list(stream_block_names)

        # get identification of requsted stream blocks
        stream_blocks_handler = self._stc_handler.stc_stream_block(stream_block_names)
        self._stream_blocks_presence_check(stream_blocks_handler, stream_block_names)

        return stream_blocks_handler

    def deactivate_all_stream_blocks(self):
        """Deactivate all stream blocks in current configuration."""

        all_stream_blocks = self._stc_handler.stc_stream_block()
        self._stc_handler.stc_attribute(all_stream_blocks, "Active", "FALSE")

    def activate_stream_blocks(self, stream_block_names):
        """Activate stream blocks by names.

        Stream blocks are defined in a list of stream block names.
        Method first disables all stream block by setting its property
        'Active' to 'FALSE'. Then, all selected stream blocks are
        activated.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of stream block names from current
            STC configuration.
        """

        # deactivate all stream blocks
        self.deactivate_all_stream_blocks()

        # activate requested stream blocks
        stream_blocks = self._stream_blocks_handler(stream_block_names)
        self._stc_handler.stc_attribute(stream_blocks, "Active", "TRUE")

    def set_stream_blocks_vlan(self, stream_block_names, vlan_id):
        """Set VLAN ID for stream blocks selected by names.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of stream block names from current
            STC configuration.
        vlan_id : int or str
            VLAN ID to set. Value is converted to str.
        """

        stream_blocks = self._stream_blocks_handler(stream_block_names)
        # access VLAN handler in a chain of stream block childs
        eth = self._stc_handler.stc_attribute(stream_blocks, "children-ethernet:EthernetII")
        vlans = self._stc_handler.stc_attribute(eth, "children-vlans")
        vlan_handler = self._stc_handler.stc_attribute(vlans, "children-vlan")
        # set VLAN ID
        self._stc_handler.stc_attribute(vlan_handler, "ID", str(vlan_id))

    def delete_stream_blocks_vlan(self, stream_block_names):
        """Delete VLANs of stream blocks selected by names.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of stream block names from current
            STC configuration.
        """

        stream_blocks = self._stream_blocks_handler(stream_block_names)
        eth = self._stc_handler.stc_attribute(stream_blocks, "children-ethernet:EthernetII")
        vlans = self._stc_handler.stc_attribute(eth, "children-vlans")
        self._stc_handler.stc_delete(vlans)

    def set_stream_blocks_dst_mac(self, stream_block_names, dst_mac):
        """Set destination MAC address for passed stream blocks.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of names from current
            STC configuration.
        dst_mac : str
            Destination MAC address to be set in the streamblock. The format
            follows the standard 'XX:XX:XX:XX:XX:XX'.
        """

        stream_blocks = self._stream_blocks_handler(stream_block_names)
        # access dst MAC address handler
        eth = self._stc_handler.stc_attribute(stream_blocks, "children-ethernet:EthernetII")
        self._stc_handler.stc_attribute(eth, "dstMac", dst_mac)

    def set_stream_blocks_src_mac(self, stream_block_names, src_mac):
        """Set source MAC address for passed stream blocks.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of names from current
            STC configuration.
        src_mac : str
            Source MAC address to be set in the streamblock. The format
            follows the standard 'XX:XX:XX:XX:XX:XX'.
        """

        stream_blocks = self._stream_blocks_handler(stream_block_names)
        # access src MAC address handler
        eth = self._stc_handler.stc_attribute(stream_blocks, "children-ethernet:EthernetII")
        self._stc_handler.stc_attribute(eth, "srcMac", src_mac)

    def set_device_vlan(self, device_names, vlan_id):
        """Set VLAN ID on devices selected by names.

        Parameters
        ----------
        device_names : str or list(str)
            Device name or list of device names from current STC
            configuration.
        vlan_id : int or str
            VLAN ID to set. Value is converted to str.
        """

        device_names = self._object_name_list(device_names)
        devices = self._stc_handler.stc_device(device_names)
        vlan_handler = self._stc_handler.stc_attribute(devices, "children-VlanIf")
        self._stc_handler.stc_attribute(vlan_handler, "VlanId", str(vlan_id))

    def delete_device_vlan(self, device_names):
        """Delete VLANs of devices selected by names.

        Parameters
        ----------
        device_names : str or list(str)
            Device name or list of device names from current STC
            configuration.
        """

        device_names = self._object_name_list(device_names)
        devices = self._stc_handler.stc_device(device_names)
        vlan = self._stc_handler.stc_attribute(devices, "children-VlanIf")
        upper_layer = [
            self._stc_handler.stc_attribute(vlan, "StackedOnEndpoint-Sources")[0][0].split()
        ]
        lower_layer = [self._stc_handler.stc_attribute(vlan, "StackedOnEndpoint-Targets")[0][0]]
        self._stc_handler.stc_attribute(upper_layer, "StackedOnEndpoint-Targets", lower_layer)
        self._stc_handler.stc_delete(vlan)

    def set_device_mac(self, device_names, mac):
        """Set MAC address on devices selected by names.

        Parameters
        ----------
        device_names : str or list(str)
            Device name or list of device names from current STC
            configuration.
        mac : str
            MAC address to set on provided devices.
        """

        device_names = self._object_name_list(device_names)
        devices = self._stc_handler.stc_device(device_names)
        eth_handler = self._stc_handler.stc_attribute(devices, "children-EthIIIf")
        self._stc_handler.stc_attribute(eth_handler, "SourceMac", mac)

    def configure_stream_blocks_vlan(self, stream_block_names, vlan_id):
        """Configure VLAN for stream blocks selected by names.

        Parameters
        ----------
        stream_block_names : str or list(str)
            Stream block name or list of stream block names from current
            STC configuration.
        vlan_id : int or str or None
            VLAN ID to set (value is converted to str) or None to remove VLAN.
        """

        if vlan_id:
            self.set_stream_blocks_vlan(stream_block_names, vlan_id)
        else:
            self.delete_stream_blocks_vlan(stream_block_names)

    def configure_device_vlan(self, device_names, vlan_id):
        """Configure VLAN on devices selected by names.

        Parameters
        ----------
        device_names : str or list(str)
            Device name or list of device names from current STC
            configuration.
        vlan_id : int or str or None
            VLAN ID to set (value is converted to str) or None to remove VLAN.
        """

        if vlan_id:
            self.set_device_vlan(device_names, vlan_id)
        else:
            self.delete_device_vlan(device_names)

    def set_stream_blocks_packet_length(self, stream_blocks_names, packet_length):
        """Set packet length for provided stream block names.

        Parameters
        ----------
        stream_blocks_names : str or list(str)
            Stream block names to be configured.
        packet_length : int
            Packet length in bytes.
        """

        if isinstance(stream_blocks_names, str):
            stream_blocks_names = [stream_blocks_names]

        for block in stream_blocks_names:
            self._stc_handler.stc_set_stream_block_packet_length(block, packet_length)

    def set_port_load(self, port_load_type, port_load_value):
        """Set port load on spirent port.

        Port load can be set by percentage (0 to 100% of maximal link
        capacity), frames per second or bits per second.

        Parameters
        ----------
        port_load_type : str
            Type of port load. Accepted values are:
            - perc : percentage of maximal link capacity,
            - fps : frames per second,
            - bps, kbps, mbps, gbps : bits (kilobits, megabits,
            gigabits) per second.
        port_load_value : int
            Port load value.

        Raises
        ------
        ValueError
            If invalid port load type is passed.
        """

        pl_type = port_load_type.lower()

        pl_value = port_load_value
        if pl_type == "kbps":
            pl_value *= 1000
            pl_type = "bps"
        elif pl_type == "mbps":
            pl_value *= 1000 * 1000
            pl_type = "bps"
        elif pl_type == "gbps":
            pl_value *= 1000 * 1000 * 1000
            pl_type = "bps"

        if pl_type == "perc":
            self._stc_handler.stc_set_port_load("perc", pl_value)
        elif pl_type == "fps":
            self._stc_handler.stc_set_port_load("fps", pl_value)
        elif pl_type == "bps":
            self._stc_handler.stc_set_port_load("bps", pl_value)
        else:
            raise ValueError("Invalid port load type '{}'.".format(pl_type))

    def stream_blocks_arpnd_resolved(self, stream_blocks):
        """Check ARP/ND status of selected stream blocks.

        If some stream block have ARP/ND unresolved, function tries to
        resolve ARP/ND using spirent. If ARP/ND remains unresolved
        False is returned.

        Parameters
        ----------
        stream_blocks : list(str)
            List of stream block names for which an ARP/ND status is
            checked.

        Returns
        -------
        bool
            True when all stream blocks have ARP/ND resolved, False
            otherwise.
        """

        arpnd_ok = []
        for sb_name in stream_blocks:
            sb = self._stc_handler.stc_stream_block(sb_name)
            arpnd_status = self._stc_handler.stc_attribute(sb, "IsArpResolved")[0][0]
            arpnd_ok.append(arpnd_status.lower())

        if "false" in arpnd_ok:
            self._stc_handler.stc_start_arpnd()
            for sb_name in stream_blocks:
                arpnd_fixed = self._stc_handler.stc_attribute(sb, "IsArpResolved")[0][0]
                if arpnd_fixed.lower() != "true":
                    return False

        return True

    def _link_is_up(self) -> bool:
        status = self._stc_handler.stc_get_link_status()
        self._logger.debug(f"Link status: {status}")
        return status == "UP"

    def _wait_for_link_up(self):
        assert wait_until_condition(
            lambda: self._link_is_up(), timeout=self._link_wait_timeout, sleep_step=1.0
        ), f"Spirent link is {self._stc_handler.stc_get_link_status()}"

    def generate_traffic(self, duration, use_analyzer=False):
        """Perform packets sending based on current stream blocks setup
        using STC generators. Usage of analyzers is optional.

        Parameters
        ----------
        duration : int
            Duration of traffic generation in seconds. Amount of traffic
            depends on configured load.
        use_analyzer : bool
            Flag whether to use analyzer.
        """

        self._stc_handler.stc_set_traffic_gen_seconds(duration)

        if use_analyzer:
            self._stc_handler.stc_start_analyzers()

        self._wait_for_link_up()

        self._stc_handler.stc_start_generators()
        self._stc_handler.stc_stop_generators()

        time.sleep(5)  # Extra 5s as it is used in STC docs (waiting for analyzers, stats, etc.)

        if use_analyzer:
            self._stc_handler.stc_stop_analyzers()

        self._stc_handler.stc_refresh_results()

    @staticmethod
    def get_flat_stream_results(results):
        """Make flat list from results.

        Results come in a structure [[['values1']], [['values2']]].
        This method makes a flat list from this nested lists.

        Parameters
        ----------
        results : list(list(list))
            Data in a structure: [[['values1']], [['values2']]]

        Returns
        -------
        list
            List of extracted values ['values1', 'values2']
        """

        flat_results = []
        for result_l1 in results:
            for result_l2 in result_l1:
                for result_l3 in result_l2:
                    flat_results.append(result_l3)

        return flat_results

    def get_port_latency_stats(self, port=0):
        """Retrieve port latency statistics from STC.

        Returns
        -------
        dict
            Dictionary with extracted stats.
        """

        latency_counters = [
            ("AvgLatency", float),
            ("MaxLatency", float),
            ("MinLatency", float),
            ("TotalLatency", float),
        ]

        stats = {}

        for key, val_type in latency_counters:
            val = self._stc_handler.stc_port_latency_results(key)[port]
            stats[key] = val_type(val)

        return stats

    def filter_ipv4_destination_address(self):
        """Configure STC analyzer to filter destination IPv4 addresses."""

        self._logger.debug("Configure STC analyzer to filter destination IPv4 addresses.")
        IPV4_DEST_ADDR_FILTER = """
            <frame>
                <config>
                    <pdus>
                        <pdu name="eth1" pdu="ethernet:EthernetII"></pdu>
                            <pdu name="ip_1" pdu="ipv4:IPv4">
                                <destAddr filterMinValue="000.000.000.000"
                                filterMaxValue="255.255.255.255">255.255.255.255</destAddr>
                            </pdu>
                        </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([IPV4_DEST_ADDR_FILTER])

    def filter_ipv6_destination_address(self):
        """Configure STC analyzer to filter destination IPv6 addresses."""

        self._logger.debug("Configure STC analyzer to filter destination IPv6 addresses.")
        IPV6_DEST_ADDR_FILTER = """
            <frame>
                <config>
                    <pdus>
                        <pdu name="eth1" pdu="ethernet:EthernetII"></pdu>
                        <pdu name="proto1" pdu="ipv6:IPv6">
                            <destAddr filterMinValue="::0"
                            filterMaxValue="::FFFF:FFFF:FFFF:FFFF:FFFF:FFFF">
                            ::FFFF:FFFF:FFFF:FFFF</destAddr>
                        </pdu>
                    </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([IPV6_DEST_ADDR_FILTER])

    def filter_ttl_in_ipv4_packets(self):
        """Configure STC analyzer to filter TTL values in IPv4 packets."""

        self._logger.debug("Configure STC analyzer to filter TTL values is IPv4 packets.")
        IPV4_TTL_FILTER = """
            <frame>
                <config>
                    <pdus>
                        <pdu name="eth1" pdu="ethernet:EthernetII"></pdu>
                        <pdu name="ip_1" pdu="ipv4:IPv4">
                            <ttl filterMinValue="0" filterMaxValue="255">255</ttl>
                        </pdu>
                    </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([IPV4_TTL_FILTER])

    def filter_ttl_in_ipv6_packets(self):
        """Configure STC analyzer to filter TTL (hopLimit) values in IPv6 packets."""

        self._logger.debug(
            "Configure STC analyzer to filter TTL (hopLimit) values is IPv6 packets."
        )
        IPV6_TTL_FILTER = """
            <frame>
                <config>
                    <pdus>
                        <pdu name="eth1" pdu="ethernet:EthernetII"></pdu>
                        <pdu name="proto1" pdu="ipv6:IPv6">
                            <hopLimit filterMinValue="0" filterMaxValue="255">255</hopLimit>
                        </pdu>
                    </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([IPV6_TTL_FILTER])

    def filter_vlan(self):
        """Configure STC analyzer to filter VLANs."""

        self._logger.debug("Configure STC analyzer to filter VLANs.")
        VLAN_FILTER = """
            <frame>
                <config>
                    <pdus>
                        <pdu name="eth1" pdu="ethernet:EthernetII">
                            <vlans>
                                <Vlan name="Vlan">
                                    <id filterMinValue="0" filterMaxValue="4095">4095</id>
                                </Vlan>
                            </vlans>
                        </pdu>
                    </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([VLAN_FILTER])

    def filter_mac_address(self, direction):
        """Configure STC analyzer to filter MAC addresses.

        Parameters
        ----------
        direction : str
            MAC address direction. Allowed values are "src" or "dst".
        """

        assert direction == "src" or direction == "dst"

        direction_tag = "srcMac" if direction == "src" else "dstMac"
        self._logger.debug(f"Configure STC analyzer to filter {direction} MAC addresses.f")
        MAC_ADDRESS_FILTER = f"""
            <frame>
                <config>
                    <pdus>
                        <pdu name="proto1" pdu="ethernet:EthernetII">
                            <{direction_tag} filterMinValue="00:00:00:00:00:00"
                            filterMaxValue="FF:FF:FF:FF:FF:FF">FF:FF:FF:FF:FF:FF
                            </{direction_tag}>
                        </pdu>
                    </pdus>
                </config>
            </frame>
        """
        self._stc_handler.stc_analyzer_filter([MAC_ADDRESS_FILTER])
