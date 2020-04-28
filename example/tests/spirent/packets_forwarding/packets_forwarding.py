"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala, Ivan Hazucha)
Copytight: (C) 202O CESNET
License: GPL-2.0

Simple spirent example packets forwarding test.

This tests establishes connection to the spirent test center and configures it
for data forwarding. Test is represented by receiving and forwarding generated
packets back to the spirent. Test cases are peresented by various stream blocks
setup.

Test passes successfully if all received packets are forwarded back to the spirent.

If dcpro card and firmware is used enable dcpro mode via command line argument.
Other modes are not currently implemented.
"""

import os
import sys
import subprocess
import time

# Appends PYTHONPATH to enable tests framework modules access.
sys.path.append(os.path.abspath(__file__ + "/../../../../.."))
from framework import TestCaseData
from modules.spirent.stctest import StcTest

# Appends PYTHONPATH to enable DCPro FEC control auxiliary module.
sys.path.append(os.path.abspath(__file__ + "/../.."))
from _dcpro_fec._dcpro_fec import dcpro_fec_set


# ----------------------------------------------------------------------
#    TEST CASE DATA CLASS PREPARATION
# ----------------------------------------------------------------------
def _init_pf_test_case_data(self):
    """Initialization of custom test case data properties.

    For override of TestCaseData.init_test_specific_properties() method.
    """

    self.case_stream_blocks = None

TestCaseData.init_test_specific_properties = _init_pf_test_case_data


# ----------------------------------------------------------------------
#    PACKETS FORWARDING TEST CLASS
# ----------------------------------------------------------------------
class Packets_forwarding(StcTest):
    """ Class of the spirent packets forwarding test.

    Extends StcTest class by extending methods for test environemtn setup, prolog, epilog,
    pre-test and post-test phases and overriding methods for test cases setup and the test
    body.

    Attributes
    ----------
    _SPIRENT_INPUT_FILE : str
        Name of a STC configuration file.
    _DCPRO_FILTER_FILE : str
        Name of the dcpro filter configuration file.
    _DCPRO_PR_FILTER_FILE : str
        Name of the dcpro prfilter configuration file.
    _SLEEP_TIME : int
        Time length of a packet generation.
    _dpcro_filter_file : str
        Path to the dcpro filter configuration file.
    _dpcro_pr_filter_file : str
        Path to the dcpro prfilter configuration file.
    """

    _SPIRENT_INPUT_FILE = 'pkt_fwd.xml'
    _DCPRO_FILTER_FILE = 'filter.txt'
    _DCPRO_PR_FILTER_FILE = 'prfilter.txt'
    _SLEEP_TIME = 10 # seconds

    def _setup(self):
        """Perform general test environment setup.

        Extends super()._setup() by setting paths to configuration files.
        """

        super()._setup()

        self._spirent_config = os.path.join(self._dirs['config'], Packets_forwarding._SPIRENT_INPUT_FILE)
        self._dpcro_filter_file = os.path.join(self._dirs['config'], Packets_forwarding._DCPRO_FILTER_FILE)
        self._dpcro_pr_filter_file = os.path.join(self._dirs['config'], Packets_forwarding._DCPRO_PR_FILTER_FILE)


    def _set_test_cases(self):
        """Set test cases

        Overrides super()._set_test_cases().

        Create set up for packet generation from:
        - single IPv4 stream block,
        - single IPv6 stream block,
        - all IPv4 and IPv6 stream blocks.
        """

         # IPv4 packets forwarding
        test1 = TestCaseData()
        test1.case_name = "Packets forwarding, IPv4, single streamblock"
        test1.case_stream_blocks  = ['UDP-dst-192-168-1-0', ]
        self._add_testcase(test1)

        # IPv6 packets forwarding
        test2 = TestCaseData()
        test2.case_name = "Packets forwarding, IPv6, single streamblock"
        test2.case_stream_blocks  = ['UDP-IPv6-dst-2001', ]
        self._add_testcase(test2)

        # IPv4 and IPv6 packets forwarding
        test3 = TestCaseData()
        test3.case_name = "Packets forwarding, IPv4 + IPv6, all streamblocks"
        test3.case_stream_blocks  = ['UDP-dst-192-168-1-0', 'UDP-dst-192-168-2-0',
                'UDP-IPv6-dst-2001', 'UDP-IPv6-dst-2002', ]
        self._add_testcase(test3)


    def _prologue(self):
        """Perform environment preparation common for packet forwarding test cases within this test.

        Extends super()._prologue() method:
        Enables IPv6, if dcpro mode is enabled configure dcpro card for data forwarding.
        """

        super()._prologue()

        self._logger.info('Enabling IPv6 routing...')
        self._logger.info('    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0')
        result = self._execute_script('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0')
        self._check_subprocess_output(result)
        self._logger.info('    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0')
        result = self._execute_script('sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0')
        self._check_subprocess_output(result)

        if self._args.dcpro_mode:
            self._logger.info('    Setting up DCPro-spirent forwarding...')
            result = self._execute_script('nfb-eth -e1')
            self._check_subprocess_output(result,exit_on_fail=True)
            result = self._execute_script('dcprofilterctl -f {}'.format(self._dpcro_filter_file))
            self._check_subprocess_output(result,exit_on_fail=True)
            result = self._execute_script('dcproprfilterctl -l {}'.format(self._dpcro_pr_filter_file))
            self._check_subprocess_output(result,exit_on_fail=True)
            result = self._execute_script('dcprowatchdogctl -e0')
            self._check_subprocess_output(result,exit_on_fail=True)
            result = self._execute_script('dcproctl -s 1')
            self._check_subprocess_output(result,exit_on_fail=True)
            self._logger.info('    DCPro-spirent forwarding setup is completed.')

            self._logger.info('Running DCPro FEC control...')

            fec_is_set = dcpro_fec_set()
            if not self._manual_debug:
                self._stc_handler.stc_set_fec(fec_is_set)
            else:
                self._logger.info('Skipping FEC setup in spirent config. Make sure that FEC is set properly in spirent interface configuration.')
            self._logger.info('Fec is set to {}.'.format(str(fec_is_set)))
        else:
            self._logger.warn('DCPro mode is off, skipping DCPro FEC control.')


    def _epilogue(self):
        """Clean up environment set up common for packet forwarding test cases within this test.

        Extends super()._epilogue() method:
        Disables IPv6 (DCPro card configuration is not recovered and is left as is).
        """

        self._logger.info('Disabling IPv6 routing...')
        self._logger.info('    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        result = self._execute_script('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        self._check_subprocess_output(result)
        self._logger.info('    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1')
        result = self._execute_script('sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1')
        self._check_subprocess_output(result)

        super()._epilogue()


    def _pre_test(self, act_test_data):
        """Prepare test cases.

        Extends super()._pre_test():
        Configure IP addresses on the interface used for testing and turns of nocarrier
        for the interface.

        Parameters
        ----------
        act_test_data : TestCaseSetup
            Setup of the current test case.
        """

        super()._pre_test(act_test_data)


        self._logger.info('Prepairing test environment...')

        # configre interface nfb0p0
        self._logger.info('    Configure nfb0p0 interface:')
        self._logger.info('        add IPv4 address 192.168.0.11/24')
        result = self._execute_script('sudo ip addr add 192.168.0.11/24 dev nfb0p0')
        self._check_subprocess_output(result)

        self._logger.info('        add IPv6 address 2000::11/64')
        result = self._execute_script('sudo ip -6 address add 2000::11/64 dev nfb0p0')
        self._check_subprocess_output(result)

        self._logger.info('        set state of the interface to UP')
        result = self._execute_script('sudo ip link set dev nfb0p0 up')
        self._check_subprocess_output(result)

        # add routes via spirent device(192.168.0.100 and 2000::100)
        self._logger.info('    Add IP routes to table 10:')

        self._logger.info('        192.168.1.0/24 via 192.168.0.100')
        result = self._execute_script('sudo ip route add 192.168.1.0/24 via 192.168.0.100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        192.168.2.0/24 via 192.168.0.100')
        result = self._execute_script('sudo ip route add 192.168.2.0/24 via 192.168.0.100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        2001::/64 via 2000::100')
        result = self._execute_script('sudo ip -6 route add 2001::/64 via 2000::100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        2002::/64 via 2000::100')
        result = self._execute_script('sudo ip -6 route add 2002::/64 via 2000::100 table 10')
        self._check_subprocess_output(result)

        if not self._manual_debug:
            # activate streamblocks
            self._logger.info('    Configuring StreamBlocks ...')
            self._activate_stream_blocks_by_name(act_test_data.case_stream_blocks)
            self._stc_handler.stc_clear_results()

        # Set carrier (DCPro)
        if self._args.dcpro_mode:
            self._logger.info('    Turning off "nocarrier" in /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            result = self._execute_script('echo 0 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            self._check_subprocess_output(result)

        self._logger.info('Environment prepared successfully.\n')


    def _post_test(self, act_test_data):
        """Cleanup test case.

        Extends super()._post_test():
        Turns of nocarrier for the interface used for testing and and delete IP configuration
        on the interface.

        Parameters
        ----------
        act_test_data : TestCaseSetup
            Setup of the current test case.
        """

        self._logger.info('\nCleaning up test environment...')

        # Set carrier (DCPro)
        if self._args.dcpro_mode:
            self._logger.info('        Turning on "nocarrier" in /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            result = self._execute_script('echo 1 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            self._check_subprocess_output(result)

        # remove routes for spirent device(192.168.0.100 and 2000::100)
        self._logger.info('    Delete IP routes from table 10:')

        self._logger.info('        192.168.1.0/24 via 192.168.0.100')
        result = self._execute_script('sudo ip route del 192.168.1.0/24 via 192.168.0.100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        192.168.2.0/24 via 192.168.0.100')
        result = self._execute_script('sudo ip route del 192.168.2.0/24 via 192.168.0.100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        2001::/64 via 2000::100')
        result = self._execute_script('sudo ip -6 route del 2001::/64 via 2000::100 table 10')
        self._check_subprocess_output(result)

        self._logger.info('        2002::/64 via 2000::100')
        result = self._execute_script('sudo ip -6 route del 2002::/64 via 2000::100 table 10')
        self._check_subprocess_output(result)

        # remove interface nfb0p0 configuration
        self._logger.info('    Clear nfb0p0 interface configuration:')

        self._logger.info('        set state of the interface to DOWN...')
        result = self._execute_script('sudo ip link set dev nfb0p0 down')
        self._check_subprocess_output(result)

        # Note: IPv6 address is removed automaticaly when interface is brought down
        self._logger.info('        IPv6 should be removed automaticaly ...')

        self._logger.info('        delete IPv4 address 192.168.0.11/24 ...')
        result = self._execute_script('sudo ip addr del 192.168.0.11/24 dev nfb0p0')
        self._check_subprocess_output(result)

        self._logger.info('Environment cleaned up successfully.\n')


    def _test(self, act_test_data):
        """Test procedures executed for every test case.

        Overrides super()._test().

        For every configured case ARP/ND is handled first. After that, packet generation
        using spirent is run for a configured time. When packet generation is completed
        test evaluation checks whether all received packets has been forwarded back to
        the spirent. Test succeedes if packet counts macthes, otherwise fails.

        Parameters
        ----------
        act_test_data : TestCaseSetup
            Setup of the current test case.
        """

        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Test environment is prepared, test body would start here (but will be skipped).')
            input("Press ENTER to proceed to next test scenario.")
            return

        self._logger.info('Running the test scenario...')

        self._logger.info('    Starting ARP/ND ...')
        self._stc_handler.stc_start_arpnd()

        self._logger.info('    Starting generator(s) ...')
        self._stc_handler.stc_start_generators()

        self._logger.info('    Waiting {} seconds ...'.format(Packets_forwarding._SLEEP_TIME))
        time.sleep(Packets_forwarding._SLEEP_TIME)

        self._logger.info('    Stopping generator(s) ...')
        self._stc_handler.stc_stop_generators()

        # get results
        frame_stats = dict()
        # sum of all packets generated by STC
        generated_frames = int(self._stc_handler.stc_generator_port_results('TotalFrameCount')[0])
        frame_stats["generated"] = generated_frames
        frame_stats["transmitted (tx)"] = 0 # For proper table row ordering ... value will be filled later
        frame_stats["received (rx)"] = 0 # For proper table row ordering ... value will be filled later

        sb_failed = {}
        tx_total = 0
        rx_total = 0
        # All traffic from legitimate sources should be send back
        for sb in act_test_data.case_stream_blocks:
            assert self._stc_handler.stc_rx_stream_block_results(self._stc_handler.stc_stream_block(sb), "Active")[0][0] == 'true', "TODO osetrit lepe"

            fc_tx = self._stc_handler.stc_tx_stream_block_results(self._stc_handler.stc_stream_block(sb), "FrameCount")[0][0]
            fc_rx = self._stc_handler.stc_rx_stream_block_results(self._stc_handler.stc_stream_block(sb), "FrameCount")[0][0]

            tx_total += int(fc_tx)
            rx_total += int(fc_rx)
            frame_stats["-> tx streamblock " + sb] = fc_tx
            frame_stats["<- rx streamblock " + sb] = fc_rx

            if fc_tx != fc_rx:
                sb_failed[sb] = "Some traffic has been dropped."

        frame_stats["transmitted (tx)"] = tx_total
        frame_stats["received (rx)"] = rx_total

        self._print_frame_stats(frame_stats, 1)

        if sb_failed:
            err_str =  "Following streamblock(s) frame count is wrong:"
            for sb, reason in sb_failed.items():
                err_str += "\n    " + sb + ": " + reason

            self._test_result_fail(act_test_data.case_name, err_str)
            return

        self._test_result_success(act_test_data.case_name)


    def _print_frame_stats(self, stc_stats, indentation_level:int):
        self._logger.info("{}Printing STC frame statistics:".format(indentation_level*4*" "))

        max_key_len = max([len(k) for k in stc_stats.keys()]) +3
        max_val_len = max([len(str(v)) for v in stc_stats.values()])
        max_val_len += max_val_len//3 + 3

        self._logger.info("%s     %-*s | %-*s " % (indentation_level*4*" ", max_key_len, "STC frames", max_val_len, "Frame count"))
        self._logger.info(indentation_level*4*" " + "     " + max_key_len*"=" + "=|=" + max_val_len*"=" + "=")
        for key, val in stc_stats.items():
            self._logger.info("%s     %-*s | %*s " % (indentation_level*4*" ", max_key_len, key, max_val_len, "{:,d}".format(int(val)).replace(",", " ")))

