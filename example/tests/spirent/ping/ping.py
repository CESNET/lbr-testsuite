"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Simple example echo test.
"""

import os
import sys
import subprocess

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
        self.ping_command = None


# ----------------------------------------------------------------------
#    HELLO TEST CLASS
# ----------------------------------------------------------------------
class Ping(StcTest):

    SPIRENT_INPUT_FILE = 'ping.xml'
    DCPRO_FILTER_FILE = 'filter.txt'
    DCPRO_PR_FILTER_FILE = 'prfilter.txt'


    def _setup(self):
        super()._setup()

        self._spirent_config = os.path.join(self._dirs['test'], Ping.TEST_CASE_CONFIG_DIR, Ping.SPIRENT_INPUT_FILE)
        self._dpcro_filter_file = os.path.join(self._dirs['src'], Ping.DCPRO_FILTER_FILE)
        self._dpcro_pr_filter_file = os.path.join(self._dirs['src'], Ping.DCPRO_PR_FILTER_FILE)


    def _set_test_cases(self):
        # Test if device respond for ping (IPv4)
        test_ping_ipv4 = TestData()
        test_ping_ipv4.case_name = "Routing tests - IPv4 ping respond."
        test_ping_ipv4.ping_command = 'sudo ping -c 5 192.168.0.100'
        self.add_testcase(test_ping_ipv4)

        # Test if device respond for ping (IPv6)
        test_ping_ipv6 = TestData()
        test_ping_ipv6.case_name = "Routing tests - IPv6 ping respond"
        test_ping_ipv6.ping_command = 'sudo ping -6 -c 5 2000::100'
        self.add_testcase(test_ping_ipv6)


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

        # ping device emulated on STC
        self._logger.info('    Testing response for ping...')

        self._logger.info(act_test_data.ping_command)
        output = subprocess.run(act_test_data.ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
        self._logger.info(output.stdout)
        if output.returncode == 0:
            self.test_result_success(act_test_data.case_name)
        else:
            self.test_result_fail(act_test_data.case_name, 'Device did not respond for the ping.')
            return
