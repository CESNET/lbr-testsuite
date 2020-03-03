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

from spirent.spirentlib import StcHandler

# Appends PYTHONPATH to enable testsuite module access
sys.path.append(os.path.abspath(__file__ + "/../../../"))
from src.basetest import BaseTest
from src.logger import Logger
from src.testresult import TestResult


# ----------------------------------------------------------------------
#     TEST CLASS
# ----------------------------------------------------------------------

class StcTest(BaseTest):

    SERVER_PORT = 42000  # server part of StcHandler listens on this port number

    def __init__(self, args, output_dir, logger=None, use_fec=False):
        super().__init__(args, output_dir, logger)

        self._port = args.port
        self._chassis = args.chassis

        self._stc_handler = None
        self._ndp_read_process = None
        self._ndp_generate_process = None

        self._ddp_act_test_logfile = None


    def _setup(self):
        """
        Performs BaseTest setup and sets STC handler.
        """
        super()._setup()

        if not self._manual_debug:
            self._set_stc_handler()


    def _prologue(self):
        """
        Connects to Spirent TestCenter terminal server, loads STC configuration from XML file,
        connects to STC chassis and reserves STC port, reboots DCPRO card and setup firmware
        modules via setup.sh script
        """
        super()._prologue()
        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping STC reservation and preparation.')
        else:
            self._logger.info('Connecting to STC terminal server: {}:{} ...'.format(self._server, self.SERVER_PORT))
            self._stc_handler.stc_api_connect(self._server, self.SERVER_PORT)

            self._logger.info('Initializing Spirent Test Center ...')
            self._logger.info('Loading STC configuration: {} ...'.format(self._files['stc-xml']))
            self._stc_handler.stc_init(self._files['stc-xml'])

            self.set_fec_in_config_xml()

            self._logger.info('Connecting to STC chassis: {}...'.format(self._chassis))
            self._logger.info('Reserving STC port: {} ...'.format(self._port))
            self._stc_handler.stc_connect(self._chassis, self._port)


    def _epilogue(self):
        """
        Disconnects from Spirent TestCenter terminal server, and cleans local enviroment
        via clean.sh script
        """
        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping STC disconnecting and cleanup.')
        else:
            self._logger.info('Disconnecting from Spirent Test Center ...')
            self._stc_handler.stc_disconnect()

    def _pre_test(self, act_test_data):
        """
        Procedures before particular test case execution.
        :param values: TestData object that represents particular test case
        """
        super()._pre_test(act_test_data)

        suffix = '.log'
        if self._manual_debug:
            suffix = '_MANUAL_DEBUG.log'

        self._ddp_act_test_logfile = self._dirs['ddpd_logs'] + '/ddpd_stc_test-' + Logger._get_file_prefix_date() + suffix
        result = self.execute_script('sudo sed -i -e "s?[[:blank:]][[:blank:]]*log-file:.*?    log-file: \'{}\'?g" {}'.format(self._ddp_act_test_logfile, self._files['ddpd_config']))
        self._log_subprocess_output(result)

    # -----------------------------------------------------------------------
    # SET METHODS
    # -----------------------------------------------------------------------

    def _set_stc_handler(self):
        """
        Create Stc API handler and establish connection
        """
        self._stc_handler = StcHandler()

    # -----------------------------------------------------------------------
    # DCPRO METHODS
    # -----------------------------------------------------------------------

    def _start_ndp_read(self):
        """
        Start ndp-tool in mode 'read' in new process and store process ID into variable _ndp_read_process.
        This method need to be called before STC start generate packets(on the beginning of the test case).
        Method _get_ndp_read_packet_count() must be called at the end of test case to ensure terminating of
        process created by this method. If ndp-read process is running and this method is called exception
        is raised.
        """
        self._logger.info('Starting ndp-read ...')

        if self._ndp_read_process is not None:
            err_msg = "Call ndp-tool while other ndp-read process is running"
            self._ndp_read_process.send_signal(signal.SIGINT)
            raise RuntimeWarning(err_msg)

        command = 'ndp-tool read -I0'
        self._logger.info('{}'.format(command))
        self._ndp_read_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    def _start_ndp_generate(self, packet_size):
        """
        Start ndp-tool in mode 'generate' in new process and store process ID into variable _ndp_generate_process.
        Ndp-tool will generate packet to all channels and packets will have size defined by input parameter.
        Method _stop_ndp_generate() must be called on the end of test case to ensure terminating of
        process created by this method. If ndp-generate process is running and this method is called exception
        is raised.
        :param packet_size: size of packets that will be generated
        """
        self._logger.info('Starting ndp-generate ...')

        if self._ndp_generate_process is not None:
            err_msg = "Call ndp-generate while other ndp-generate process is running"
            self._ndp_generate_process.send_signal(signal.SIGINT)
            raise RuntimeWarning(err_msg)

        command = 'ndp-tool generate -I0 -s {}'.format(packet_size)
        self._logger.info('{}'.format(command))
        self._ndp_generate_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    def _get_ndp_read_packet_count(self):
        """
        Return count of packets forwarded to software part of DCPRO and terminate ndp-tool.
        This method can be used only if ndp-tool is running in 'read' mode and its process ID
        is stored in variable _ndp_generate_process. Otherwise exception is raised.
        Process with ID stored in _ndp_read_process is terminated by SIGINT.
        :return: count of packets forwarded to software part of DCPRO
        """
        self._logger.info('Terminating ndp-read ...')

        if self._ndp_read_process is None:
            err_msg = "Error can not read packet from ndp-tool, because ndp-read process does not running!"
            raise RuntimeWarning(err_msg)

        self._ndp_read_process.send_signal(signal.SIGINT)
        stdout, stderr = self._ndp_read_process.communicate()
        self._ndp_read_process.terminate()
        self._ndp_read_process = None

        stdout = stdout.decode("utf-8")
        stderr = stderr.decode("utf-8")

        if stderr != '':
            err_msg = "An error occurred while using ndp-tool! Error message :\n{}".format(stderr)
            raise RuntimeWarning(err_msg)

        result_lines = stdout.split('\n')
        packet_count = None

        for line in result_lines:
            match = re.match(r"^(Packets).*:\s*([0-9]+)", line)
            if match:
                packet_count = match.group(2)

        if packet_count is None:
            err_msg = "Error ndp-tool output does not match pattern 'Packets : [number]'!"
            raise RuntimeWarning(err_msg)

        return packet_count

    def _stop_ndp_generate(self):
        """
        Stop generating of packets and terminate ndp-tool.
        This method can be used only if ndp-tool is running in 'generate' mode
        and its process ID is stored in variable _ndp_generate_process.
        Otherwise exception is raised. Process with ID stored in _ndp_tool_process is terminated by SIGINT.
        """
        self._logger.info('Terminating ndp-generate ...')

        if self._ndp_generate_process is None:
            err_msg = "Error can not stop ndp-generate, because ndp-generate process does not running!"
            raise RuntimeWarning(err_msg)

        self._ndp_generate_process.send_signal(signal.SIGINT)
        stdout, stderr = self._ndp_generate_process.communicate()
        self._ndp_generate_process.terminate()
        self._ndp_generate_process = None

        stderr = stderr.decode("utf-8")

        if stderr != '':
            err_msg = "An error occurred while using ndp-tool! Error message :\n{}".format(stderr)
            raise RuntimeWarning(err_msg)

    # -----------------------------------------------------------------------
    # SPIRENT TESTCENTER METHODS
    # -----------------------------------------------------------------------

    def _activate_stream_blocks_by_name(self, block_names: list):
        """
        Activate stream blocks defined List of stream block Names, other set to Active = FALSE.
        Rise exception if passed argument is not of type list, or if any of stream blocks form list
        is not defined in used STC configuration.
        :param block_names: list of strings that are Names of stream block from STC configuration
        """

        if not isinstance(block_names, list):
            err_msg = "Stream blocks must be defined in List of strings, but passed '{}'!".format(type(block_names))
            raise TypeError(err_msg)

        # deactivate all stream blocks
        all_streamblock = self._stc_handler.stc_stream_block()
        self._stc_handler.stc_attribute(all_streamblock, 'Active', 'FALSE')

        # get identification of requred stream blocks
        required_streamblock = self._stc_handler.stc_stream_block(block_names)

        if len(required_streamblock) == 0 or len(required_streamblock) != len(block_names):
            err_msg = "Any of defined stream blocks '{}' is not defined in STC configuration!".format(block_names)
            raise ValueError(err_msg)

        for index, sb in enumerate(required_streamblock):
            if len(sb) != 1:
                err_msg = "Stream block '{}' is not defined in STC configuration!".format(block_names[index])
                raise ValueError(err_msg)

        # activate required stream blocks
        self._stc_handler.stc_attribute(required_streamblock, 'Active', 'TRUE')

    def set_fec_in_config_xml(self):
        """
        Set FEC (forward error correction) in xml configuration based on car used.
        """
        self._logger.info("Preparing STC config file...")

        fec_supported = detectcard.card_support_fec()

        if fec_supported is None:
            err_msg = "Unable to detect card type whle setting up FEC.".format()
            raise RuntimeError(err_msg)

        xpath = ['StcSystem/Project/Port/Ethernet100GigFiber']
        fec_handler = self._stc_handler.stc_object_xpath(xpath)

        if fec_supported:
            self._logger.info("    Turning FEC on...")
            self._stc_handler.stc_attribute(fec_handler, 'ForwardErrorCorrection', "True")
        else:
            self._logger.info("    Turning FEC off...")
            self._stc_handler.stc_attribute(fec_handler, 'ForwardErrorCorrection', "False")

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

    def print_frame_stats(self, stc_stats, indentation_level:int):
        # TODO check stc_stats: dict("str": int)
        self._logger.info("{}Printing STC frame statistics:".format(indentation_level*4*" "))

        max_key_len = max([len(k) for k in stc_stats.keys()]) +3
        max_val_len = max([len(str(v)) for v in stc_stats.values()])
        max_val_len += max_val_len//3 + 3

        # self._logger.info("    +-" + (max_key_len + max_val_len+3)*"-" + "-+")
        self._logger.info("%s     %-*s | %-*s " % (indentation_level*4*" ", max_key_len, "STC frames", max_val_len, "Frame count"))
        self._logger.info(indentation_level*4*" " + "     " + max_key_len*"=" + "=|=" + max_val_len*"=" + "=")
        for key, val in stc_stats.items():
            self._logger.info("%s     %-*s | %*s " % (indentation_level*4*" ", max_key_len, key, max_val_len, "{:,d}".format(int(val)).replace(",", " ")))
        # self._logger.info("    +-" + (max_key_len + max_val_len+3)*"-" + "-+")
