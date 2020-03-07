"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala, Ivan Hazucha)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Base class for tests using Spirent TestCenter.
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
from framework.basetest import BaseTest
from framework.logger import Logger
from framework.testresult import TestResult


# ----------------------------------------------------------------------
#    SPIRENT TEST CENTER TEST CLASS
# ----------------------------------------------------------------------

class StcTest(BaseTest):

    SERVER_PORT = 42000  # server part of StcHandler listens on this port number

    def __init__(self, args, output_dir, logger=None, use_fec=False):
        super().__init__(args, output_dir, logger)

        self._manual_debug = args.manual_debug

        self._stc_handler = None
        self._ndp_read_process = None
        self._ndp_generate_process = None

        # Set path to spirent xml configuration within a test
        self._spirent_config = None


    def _setup(self):
        """
        Performs BaseTest setup and sets STC handler.
        """
        super()._setup()

        if not self._manual_debug:
            self._init_stc_handler()


    def _prologue(self):
        """
        Connects to Spirent TestCenter terminal server, loads STC configuration from XML file,
        connects to STC chassis and reserves STC port.
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
        """
        Disconnects from Spirent TestCenter terminal server.
        """
        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping STC disconnecting.')
        else:
            self._logger.info('Disconnecting from Spirent Test Center ...')
            self._stc_handler.stc_disconnect()

    # -----------------------------------------------------------------------
    # AUX METHODS
    # -----------------------------------------------------------------------

    def _init_stc_handler(self):
        """
        Create Stc API handler and establish connection
        """
        self._stc_handler = StcHandler()



    # -----------------------------------------------------------------------
    # SPIRENT TESTCENTER METHODS
    # -----------------------------------------------------------------------

    def _activate_stream_blocks_by_name(self, stream_block_names: list):
        """
        Activate stream blocks defined in a list of stream block names, sets
        property 'Active' to 'FALSE' for others..
        Rise exception if passed argument is not of type list, or if any of
        stream blocks form the list is not defined in used STC configuration.
        :param stream_block_names: list of string names of stream block from STC
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


    @staticmethod
    def get_flat_stream_results(results):
        """
        Make flat list from results of structure [[['values1']], [['values2']]]
        :param results: data in structure [[['values1']], [['values2']]]
        :return: list of extracted values ['values1', 'values2']
        """
        flat_results = []
        for result_l1 in results:
            for result_l2 in result_l1:
                for result_l3 in result_l2:
                    flat_results.append(result_l3)

        return flat_results


    def filter_ipv4_destination_address(self):
        """
        Configure STC analyzer to filter destination IPv4 addresses.
        """
        self._logger.info("Configure STC analyzer to filter destination IPv4 addresses...")
        IPV4_DEST_ADDR_FILTER = "<frame><config><pdus><pdu name=\"eth1\" pdu=\"ethernet:EthernetII\"></pdu><pdu name=\"ip_1\" pdu=\"ipv4:IPv4\"><destAddr filterMinValue=\"000.000.000.000\" filterMaxValue=\"255.255.255.255\">255.255.255.255</destAddr></pdu></pdus></config></frame>"
        self._stc_handler.stc_analyzer_filter([IPV4_DEST_ADDR_FILTER])


    def filter_ipv6_destination_address(self):
        """
        Configure STC analyzer to filter destination IPv6 addresses.
        """
        self._logger.info("Configure STC analyzer to filter destination IPv6 addresses...")
        IPV6_DEST_ADDR_FILTER = "<frame><config><pdus><pdu name=\"eth1\" pdu=\"ethernet:EthernetII\"></pdu><pdu name=\"proto1\" pdu=\"ipv6:IPv6\"><destAddr filterMinValue=\"::0\" filterMaxValue=\"::FFFF:FFFF:FFFF:FFFF:FFFF:FFFF\">::FFFF:FFFF:FFFF:FFFF</destAddr></pdu></pdus></config></frame>"
        self._stc_handler.stc_analyzer_filter([IPV6_DEST_ADDR_FILTER])


    def filter_ttl_in_ipv4_packets(self):
        """
        Configure STC analyzer to filter TTL values is IPv4 packets.
        """
        self._logger.info("Configure STC analyzer to filter TTL values is IPv4 packets...")
        IPV4_TTL_FILTER = "<frame><config><pdus><pdu name=\"eth1\" pdu=\"ethernet:EthernetII\"></pdu><pdu name=\"ip_1\" pdu=\"ipv4:IPv4\"><ttl filterMinValue=\"0\" filterMaxValue=\"255\">255</ttl></pdu></pdus></config></frame>"
        self._stc_handler.stc_analyzer_filter([IPV4_TTL_FILTER])


    def filter_ttl_in_ipv6_packets(self):
        """
        Configure STC analyzer to filter TTL (hopLimit) values is IPv6 packets.
        """
        self._logger.info("Configure STC analyzer to filter TTL (hopLimit) values is IPv6 packets...")
        IPV6_TTL_FILTER = "<frame><config><pdus><pdu name=\"eth1\" pdu=\"ethernet:EthernetII\"></pdu><pdu name=\"proto1\" pdu=\"ipv6:IPv6\"><hopLimit filterMinValue=\"0\" filterMaxValue=\"255\">255</hopLimit></pdu></pdus></config></frame>"
        self._stc_handler.stc_analyzer_filter([IPV6_TTL_FILTER])

