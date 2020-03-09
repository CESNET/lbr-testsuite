"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2020 CESNET
    Licence: GPL-2.0

    Description: Simple spirent example packets forwarding test.
"""

import os
import sys
import subprocess
import time

# Appends PYTHONPATH to enable tests framework modules access.
sys.path.append(os.path.abspath(__file__ + "/../../../../.."))
from modules.spirent.stctest import StcTest

# Appends PYTHONPATH to enable DCPro FEC control auxiliary module.
sys.path.append(os.path.abspath(__file__ + "/../.."))
from _dcpro_fec._dcpro_fec import dcpro_fec_set


# ----------------------------------------------------------------------
#    TEST DATA CLASS
# ----------------------------------------------------------------------
class TestData:

    def __init__(self):
        self.case_name = None
        self.case_stream_blocks = None


# ----------------------------------------------------------------------
#    HELLO TEST CLASS
# ----------------------------------------------------------------------
class Packets_forwarding(StcTest):

    SPIRENT_INPUT_FILE = 'pkt_fwd.xml'
    DCPRO_FILTER_FILE = 'filter.txt'
    DCPRO_PR_FILTER_FILE = 'prfilter.txt'
    SLEEP_TIME = 10 # seconds

    def _setup(self):
        super()._setup()

        self._spirent_config = os.path.join(self._dirs['test'], Packets_forwarding.TEST_CASE_CONFIG_DIR, Packets_forwarding.SPIRENT_INPUT_FILE)
        self._dpcro_filter_file = os.path.join(self._dirs['src'], Packets_forwarding.DCPRO_FILTER_FILE)
        self._dpcro_pr_filter_file = os.path.join(self._dirs['src'], Packets_forwarding.DCPRO_PR_FILTER_FILE)


    def _set_test_cases(self):
         # IPv4 packets forwarding
        test1 = TestData()
        test1.case_name = "Packets forwarding, IPv4, single streamblock"
        test1.case_stream_blocks  = ['UDP-dst-192-168-1-0', ]
        self.add_testcase(test1)

        # IPv6 packets forwarding
        test2 = TestData()
        test2.case_name = "Packets forwarding, IPv6, single streamblock"
        test2.case_stream_blocks  = ['UDP-IPv6-dst-2001', ]
        self.add_testcase(test2)

        # IPv4 and IPv6 packets forwarding
        test3 = TestData()
        test3.case_name = "Packets forwarding, IPv4 + IPv6, all streamblocks"
        test3.case_stream_blocks  = ['UDP-dst-192-168-1-0', 'UDP-dst-192-168-2-0',
                'UDP-IPv6-dst-2001', 'UDP-IPv6-dst-2002', ]
        self.add_testcase(test3)


    def _prologue(self):
        super()._prologue()

        self._logger.info('Enabling IPv6 routing...')
        self._logger.info('    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0')
        result = self.execute_script('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=0')
        self._log_subprocess_output(result)
        self._logger.info('    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0')
        result = self.execute_script('sudo sysctl -w net.ipv6.conf.default.disable_ipv6=0')
        self._log_subprocess_output(result)

        if self._args.dcpro_mode:
            self._logger.info('    Setting up DCPro-spirent forwarding...')
            result = self.execute_script('nfb-eth -e1')
            self._log_subprocess_output(result,exit_on_fail=True)
            result = self.execute_script('dcprofilterctl -f {}'.format(self._dpcro_filter_file))
            self._log_subprocess_output(result,exit_on_fail=True)
            result = self.execute_script('dcproprfilterctl -l {}'.format(self._dpcro_pr_filter_file))
            self._log_subprocess_output(result,exit_on_fail=True)
            result = self.execute_script('dcprowatchdogctl -e0')
            self._log_subprocess_output(result,exit_on_fail=True)
            result = self.execute_script('dcproctl -s 1')
            self._log_subprocess_output(result,exit_on_fail=True)
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
        self._logger.info('Disabling IPv6 routing...')
        self._logger.info('    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        result = self.execute_script('sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1')
        self._log_subprocess_output(result)
        self._logger.info('    sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1')
        result = self.execute_script('sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1')
        self._log_subprocess_output(result)

        super()._epilogue()


    def _pre_test(self, act_test_data):
        super()._pre_test(act_test_data)

        # test start
        self.test_start(act_test_data.case_name)

        self._logger.info('Prepairing test environment...')

        # configre interface nfb0p0
        self._logger.info('    Configure nfb0p0 interface:')
        self._logger.info('        add IPv4 address 192.168.0.11/24')
        result = self.execute_script('sudo ip addr add 192.168.0.11/24 dev nfb0p0')
        self._log_subprocess_output(result)

        self._logger.info('        add IPv6 address 2000::11/64')
        result = self.execute_script('sudo ip -6 address add 2000::11/64 dev nfb0p0')
        self._log_subprocess_output(result)

        self._logger.info('        set state of the interface to UP')
        result = self.execute_script('sudo ip link set dev nfb0p0 up')
        self._log_subprocess_output(result)

        # add routes via spirent device(192.168.0.100 and 2000::100)
        self._logger.info('    Add IP routes to table 10:')

        self._logger.info('        192.168.1.0/24 via 192.168.0.100')
        result = self.execute_script('sudo ip route add 192.168.1.0/24 via 192.168.0.100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        192.168.2.0/24 via 192.168.0.100')
        result = self.execute_script('sudo ip route add 192.168.2.0/24 via 192.168.0.100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        2001::/64 via 2000::100')
        result = self.execute_script('sudo ip -6 route add 2001::/64 via 2000::100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        2002::/64 via 2000::100')
        result = self.execute_script('sudo ip -6 route add 2002::/64 via 2000::100 table 10')
        self._log_subprocess_output(result)

        if not self._manual_debug:
            # activate streamblocks
            self._logger.info('    Configuring StreamBlocks ...')
            self._activate_stream_blocks_by_name(act_test_data.case_stream_blocks)
            self._stc_handler.stc_clear_results()

        # Set carrier (DCPro)
        if self._args.dcpro_mode:
            self._logger.info('    Turning off "nocarrier" in /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            result = self.execute_script('echo 0 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            self._log_subprocess_output(result)

        self._logger.info('Environment prepared successfully.\n')


    def _post_test(self, act_test_data):
        self._logger.info('\nCleaning up test environment...')

        # Set carrier (DCPro)
        if self._args.dcpro_mode:
            self._logger.info('        Turning on "nocarrier" in /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            result = self.execute_script('echo 1 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            self._log_subprocess_output(result)

        # remove routes for spirent device(192.168.0.100 and 2000::100)
        self._logger.info('    Delete IP routes from table 10:')

        self._logger.info('        192.168.1.0/24 via 192.168.0.100')
        result = self.execute_script('sudo ip route del 192.168.1.0/24 via 192.168.0.100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        192.168.2.0/24 via 192.168.0.100')
        result = self.execute_script('sudo ip route del 192.168.2.0/24 via 192.168.0.100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        2001::/64 via 2000::100')
        result = self.execute_script('sudo ip -6 route del 2001::/64 via 2000::100 table 10')
        self._log_subprocess_output(result)

        self._logger.info('        2002::/64 via 2000::100')
        result = self.execute_script('sudo ip -6 route del 2002::/64 via 2000::100 table 10')
        self._log_subprocess_output(result)

        # remove interface nfb0p0 configuration
        self._logger.info('    Clear nfb0p0 interface configuration:')

        self._logger.info('        set state of the interface to DOWN...')
        result = self.execute_script('sudo ip link set dev nfb0p0 down')
        self._log_subprocess_output(result)

        # Note: IPv6 address is removed automaticaly when interface is brought down
        self._logger.info('        IPv6 should be removed automaticaly ...')

        self._logger.info('        delete IPv4 address 192.168.0.11/24 ...')
        result = self.execute_script('sudo ip addr del 192.168.0.11/24 dev nfb0p0')
        self._log_subprocess_output(result)

        self._logger.info('Environment cleaned up successfully.\n')


    def _test(self, act_test_data):
        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Test environment is prepared, test body would start here (but will be skipped).')
            input("Press ENTER to proceed to next test scenario.")
            return

        self._logger.info('Running the test scenario...')

        self._logger.info('    Starting ARP/ND ...')
        self._stc_handler.stc_start_arpnd()

        self._logger.info('    Starting generator(s) ...')
        self._stc_handler.stc_start_generators()

        self._logger.info('    Waiting {} seconds ...'.format(Packets_forwarding.SLEEP_TIME))
        time.sleep(Packets_forwarding.SLEEP_TIME)

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

        self.print_frame_stats(frame_stats, 1)

        if sb_failed:
            err_str =  "Following streamblock(s) frame count is wrong:"
            for sb, reason in sb_failed.items():
                err_str += "\n    " + sb + ": " + reason

            self.test_result_fail(act_test_data.case_name, err_str)
            return

        self.test_result_success(act_test_data.case_name)


    def print_frame_stats(self, stc_stats, indentation_level:int):
        self._logger.info("{}Printing STC frame statistics:".format(indentation_level*4*" "))

        max_key_len = max([len(k) for k in stc_stats.keys()]) +3
        max_val_len = max([len(str(v)) for v in stc_stats.values()])
        max_val_len += max_val_len//3 + 3

        self._logger.info("%s     %-*s | %-*s " % (indentation_level*4*" ", max_key_len, "STC frames", max_val_len, "Frame count"))
        self._logger.info(indentation_level*4*" " + "     " + max_key_len*"=" + "=|=" + max_val_len*"=" + "=")
        for key, val in stc_stats.items():
            self._logger.info("%s     %-*s | %*s " % (indentation_level*4*" ", max_key_len, key, max_val_len, "{:,d}".format(int(val)).replace(",", " ")))

