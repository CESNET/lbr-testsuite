"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
Copytight: (C) 202O CESNET
License: GPL-2.0

Base spirent test module. Provides a common frame for tests using spirent. This frame,
implemented thorugh StcTest class, extends parent BaseTest class:
- provides initialization of Spirent Test Center (STC) handler for STC control,
- handles connection to STC terminal server and spirent chassis on given port,
- provides STC control methods.
"""

import csv
import datetime
import fileinput
import inspect
import os
import re
import signal
import subprocess
import sys

from spirentlib.spirentlib import StcHandler

# Appends PYTHONPATH to enable testsuite module access
sys.path.append(os.path.abspath(__file__ + "/../../../"))
from framework import BaseTest, Logger, TestResult


class StcTest(BaseTest):
    """Base spirent test class extending BaseTest class.

    Attributes
    ----------
    _manual_debug : bool
        Manual debug flag. If it is set to True spirent connection related steps are skipped
        and expected to be handled manually.
    _stc_handler : StcHandler
        Handler for communication with Spirent Test Center (STC).
    _spirent_config : str
        Path to STC configuration.
    """

    """ Server part of StcHandler listens on this port number """
    SERVER_PORT = 8888

    def __init__(self, args, output_dir, logger=None):
        """
        Parameters
        ----------
        args : ArgumentParser.parseargs() populated namespace
            Set of parsed arguments.
        output_dir : str
            Path to the output directory where test outputs will be stored.
        logger : logging.Logger, optional
            Initialized logging facility object. If a logger is not passed, it is
            created later in the _setup() method.
        """

        super().__init__(args, output_dir, logger)

        self._manual_debug = args.manual_debug

        self._stc_handler = None

        # Set path to spirent xml configuration within a test
        self._spirent_config = None


    def _setup(self):
        """Perform general test environment setup.

        Extends BaseTest._setup() method:
        Checks spirent connection arguments and creates STC handler (iff manual debugging is
        turned off).
        """

        super()._setup()

        if not self._args.server:
            raise ValueError("Spirent test center server address is not configured.")
        if not self._args.chassis:
            raise ValueError("Spirent chassis address is not configured.")
        if not self._args.port:
            raise ValueError("Spirent port is not configured.")

        if not self._manual_debug:
            self._create_stc_handler()


    def _prologue(self):
        """Perform environment preparation common for all test cases within a test.

        Extends BaseTest._prologue() method:
        Initialize API for sending commands to STC over network, initialize STC environment
        and loads configuration, connects to spirent terminal server (iff manual debugging is
        turned off none of these steps is performed).
        """

        super()._prologue()

        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping STC reservation and preparation.')
        else:
            self._logger.info('Connecting to STC terminal server: {}:{} ...'.format(self._args.server, self.SERVER_PORT))
            self._stc_handler.stc_api_connect(self._args.server, self.SERVER_PORT)

            self._logger.info('Initializing Spirent Test Center ...')
            self._logger.info('Loading STC configuration: {} ...'.format(self._spirent_config))
            self._stc_handler.stc_init(self._spirent_config)

            self._logger.info('Connecting to STC chassis: {}...'.format(self._args.chassis))
            self._logger.info('Reserving STC port: {} ...'.format(self._args.port))
            self._stc_handler.stc_connect(self._args.chassis, self._args.port)


    def _epilogue(self):
        """Clean up environment set up common for all test cases within a test.

        Extends BaseTest._epilogue() method:
        Disconnects from spirent terminal server. (iff manual debugging is turned off).
        """
        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping STC disconnecting.')
        else:
            self._logger.info('Disconnecting from Spirent Test Center ...')
            self._stc_handler.stc_disconnect()

        super()._epilogue()

    # -----------------------------------------------------------------------
    # SPIRENT TESTCENTER METHODS
    # -----------------------------------------------------------------------

    def _create_stc_handler(self):
        """Create Stc API handler.
        """

        self._stc_handler = StcHandler()


    def _activate_stream_blocks_by_name(self, stream_block_names: list):
        """Activate stream blocks by names.

        Stream blocks are defined in a list of stream block names. Method first
        disables all stream block by setting its property 'Active' to 'FALSE'. Then,
        all selected stream blocks are activated.

        Parameters
        ----------
        stream_block_names : list(str)
            List of stream block names from STC configuration.

        Raises
        ------
        TypeError
            If passed argument is not of type list.
        ValueError
            If any of stream blocks from the list is not defined in used STC
            configuration.
        """

        if not isinstance(stream_block_names, list):
            err_msg = "Stream blocks must be defined as a list of strings, but passed '{}'!".format(type(stream_block_names))
            raise TypeError(err_msg)

        # deactivate all stream blocks
        all_streamblock = self._stc_handler.stc_stream_block()
        self._stc_handler.stc_attribute(all_streamblock, 'Active', 'FALSE')

        # get identification of requsted stream blocks
        requsted_streamblocks = self._stc_handler.stc_stream_block(stream_block_names)

        if len(requsted_streamblocks) == 0 or len(requsted_streamblocks) != len(stream_block_names):
            err_msg = "Some of defined stream blocks '{}' is not defined in STC configuration!".format(stream_block_names)
            raise ValueError(err_msg)

        for index, sb in enumerate(requsted_streamblocks):
            if len(sb) != 1:
                err_msg = "Stream block '{}' is not defined in STC configuration!".format(stream_block_names[index])
                raise ValueError(err_msg)

        # activate requested stream blocks
        self._stc_handler.stc_attribute(requsted_streamblocks, 'Active', 'TRUE')


    def _set_port_load(self, port_load_type, port_load_value):
        """Activate stream blocks by names.

        Stream blocks are defined in a list of stream block names. Method first
        disables all stream block by setting its property 'Active' to 'FALSE'. Then,
        all selected stream blocks are activated.

        Parameters
        ----------
        stream_block_names : list(str)
            List of stream block names from STC configuration.

        Raises
        ------
        TypeError
            If passed argument is not of type list.
        ValueError
            If any of stream blocks from the list is not defined in used STC
            configuration.
        """

        supported_port_types = ['perc', 'pps', 'fps', 'bps', 'kbps', 'mbps', 'gbps']

        pl_type = port_load_type.lower()

        if not pl_type in supported_port_types:
            raise ValueError("Invalid port load type '{}'.".format(pl_type))

        pl_value = port_load_value
        if pl_type == 'kbps':
            pl_value *= 1000
            pl_type = 'bps'
        elif pl_type == 'mbps':
            pl_value *= 1000*1000
            pl_type = 'bps'
        elif pl_type == 'gbps':
            pl_value *= 1000*1000*1000
            pl_type = 'bps'

        if pl_type == 'perc':
            self._stc_handler.stc_set_port_load('perc', pl_value)
        elif pl_type == 'pps' or pl_type == 'fps':
            self._stc_handler.stc_set_port_load('fps', pl_value)
        elif pl_type == 'bps':
            self._stc_handler.stc_set_port_load('bps', pl_value)
        else:
            assert False and "Invalid pl_type."


    @staticmethod
    def _get_flat_stream_results(results):
        """Make flat list from results.

        Results come in a structure [[['values1']], [['values2']]]. This method
        makes a flat list from this nested lists.

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


    def _filter_ipv4_destination_address(self):
        """Configure STC analyzer to filter destination IPv4 addresses.
        """

        self._logger.info("Configure STC analyzer to filter destination IPv4 addresses...")
        IPV4_DEST_ADDR_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="eth1" pdu="ethernet:EthernetII"></pdu>' \
                                '<pdu name="ip_1" pdu="ipv4:IPv4">' \
                                    '<destAddr filterMinValue="000.000.000.000" filterMaxValue="255.255.255.255">255.255.255.255</destAddr>' \
                                '</pdu>' \
                            '</pdus>' \
                    '</config>' \
                '</frame>'
        self._stc_handler.stc_analyzer_filter([IPV4_DEST_ADDR_FILTER])


    def _filter_ipv6_destination_address(self):
        """Configure STC analyzer to filter destination IPv6 addresses.
        """

        self._logger.info("Configure STC analyzer to filter destination IPv6 addresses...")
        IPV6_DEST_ADDR_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="eth1" pdu="ethernet:EthernetII"></pdu>' \
                            '<pdu name="proto1" pdu="ipv6:IPv6">' \
                                '<destAddr filterMinValue="::0" filterMaxValue="::FFFF:FFFF:FFFF:FFFF:FFFF:FFFF">::FFFF:FFFF:FFFF:FFFF</destAddr>' \
                            '</pdu>' \
                        '</pdus>' \
                    '</config>' \
                '</frame>'
        self._stc_handler.stc_analyzer_filter([IPV6_DEST_ADDR_FILTER])


    def _filter_ttl_in_ipv4_packets(self):
        """Configure STC analyzer to filter TTL values in IPv4 packets.
        """

        self._logger.info("Configure STC analyzer to filter TTL values is IPv4 packets...")
        IPV4_TTL_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="eth1" pdu="ethernet:EthernetII"></pdu>' \
                            '<pdu name="ip_1" pdu="ipv4:IPv4">' \
                                '<ttl filterMinValue="0" filterMaxValue="255">255</ttl>' \
                            '</pdu>' \
                        '</pdus>' \
                    '</config>' \
                '</frame>'
        self._stc_handler.stc_analyzer_filter([IPV4_TTL_FILTER])


    def _filter_ttl_in_ipv6_packets(self):
        """Configure STC analyzer to filter TTL (hopLimit) values in IPv6 packets.
        """

        self._logger.info("Configure STC analyzer to filter TTL (hopLimit) values is IPv6 packets...")
        IPV6_TTL_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="eth1" pdu="ethernet:EthernetII"></pdu>' \
                            '<pdu name="proto1" pdu="ipv6:IPv6">' \
                                '<hopLimit filterMinValue="0" filterMaxValue="255">255</hopLimit>' \
                            '</pdu>' \
                        '</pdus>' \
                    '</config>' \
                '</frame>'
        self._stc_handler.stc_analyzer_filter([IPV6_TTL_FILTER])


    def _filter_vlan(self):
        """Configure STC analyzer to filter VLANs.
        """

        self._logger.info("Configure STC analyzer to filter VLANs...")
        VLAN_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="eth1" pdu="ethernet:EthernetII">' \
                                '<vlans>' \
                                    '<Vlan name="Vlan">' \
                                        '<id filterMinValue="0" filterMaxValue="4095">4095</id>' \
                                    '</Vlan>' \
                                '</vlans>' \
                            '</pdu>' \
                        '</pdus>' \
                    '</config>' \
                '</frame>'
        self._stc_handler.stc_analyzer_filter([VLAN_FILTER])


    def _filter_mac_address(self, direction):
        """Configure STC analyzer to filter MAC addresses.

        Parameters
        ----------
        direction : str
            MAC address direction. Allowed values are "src" or "dst".
        """

        assert direction == "src" or direction == "dst"

        direction_tag = "srcMac" if direction == "src" else "dstMac"

        self._logger.info("Configure STC analyzer to filter {} MAC addresses...".format(direction))
        MAC_ADDRESS_FILTER = \
                '<frame>' \
                    '<config>' \
                        '<pdus>' \
                            '<pdu name="proto1" pdu="ethernet:EthernetII">' \
                                '<{} filterMinValue="00:00:00:00:00:00" filterMaxValue="FF:FF:FF:FF:FF:FF">FF:FF:FF:FF:FF:FF</{}>' \
                            '</pdu>' \
                        '</pdus>' \
                    '</config>' \
                '</frame>'.format(direction_tag, direction_tag)
        self._stc_handler.stc_analyzer_filter([MAC_ADDRESS_FILTER])
