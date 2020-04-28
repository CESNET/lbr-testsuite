"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala, Ivan Hazucha)
Copytight: (C) 202O CESNET
License: GPL-2.0

Simple spirent example ping test.

This tests establishes connection to the spirent test center and configures it
for data forwarding. Test is represented by exectuion of ping commands first,
for IPv4 than for IPv6.

Result of test cases depends on result of ping commands.

If dcpro card and firmware is used enable dcpro mode via command line argument.
Other modes are not currently implemented.
"""

import os
import sys
import subprocess

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
def _init_ping_test_case_data(self):
    """Initialization of custom test case data properties.

    For override of TestCaseData.init_test_specific_properties() method.
    """

    self.ping_command = None

TestCaseData.init_test_specific_properties = _init_ping_test_case_data


# ----------------------------------------------------------------------
#    HELLO TEST CLASS
# ----------------------------------------------------------------------
class Ping(StcTest):
    """ Class of the spirent ping test.

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
    _dpcro_filter_file : str
        Path to the dcpro filter configuration file.
    _dpcro_pr_filter_file : str
        Path to the dcpro prfilter configuration file.
    """

    _SPIRENT_INPUT_FILE = 'ping.xml'
    _DCPRO_FILTER_FILE = 'filter.txt'
    _DCPRO_PR_FILTER_FILE = 'prfilter.txt'


    def _setup(self):
        """Perform general test environment setup.

        Extends super()._setup() by setting paths to configuration files.
        """

        super()._setup()

        self._spirent_config = os.path.join(self._dirs['config'], Ping._SPIRENT_INPUT_FILE)
        self._dpcro_filter_file = os.path.join(self._dirs['config'], Ping._DCPRO_FILTER_FILE)
        self._dpcro_pr_filter_file = os.path.join(self._dirs['config'], Ping._DCPRO_PR_FILTER_FILE)


    def _set_test_cases(self):
        """Set test cases

        Overrides super()._set_test_cases().

        Create set up for IPv4 and IPv6 ping test cases.
        """

        # Test if device respond for ping (IPv4)
        test_ping_ipv4 = TestCaseData()
        test_ping_ipv4.case_name = "Routing tests - IPv4 ping respond."
        test_ping_ipv4.ping_command = 'sudo ping -c 5 192.168.0.100'
        self._add_testcase(test_ping_ipv4)

        # Test if device respond for ping (IPv6)
        test_ping_ipv6 = TestCaseData()
        test_ping_ipv6.case_name = "Routing tests - IPv6 ping respond"
        test_ping_ipv6.ping_command = 'sudo ping -6 -c 5 2000::100'
        self._add_testcase(test_ping_ipv6)


    def _prologue(self):
        """Perform environment preparation common for ping test cases within this test.

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
            self._logger.warn('DCPro mode is off, skipping DCPro configuration.')


    def _epilogue(self):
        """Clean up environment set up common for ping test cases within this test.

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
        act_test_data : TestCaseData
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
        act_test_data : TestCaseData
            Setup of the current test case.
        """

        self._logger.info('\nCleaning up test environment...')

        # Set carrier (DCPro)
        if self._args.dcpro_mode:
            self._logger.info('        Turning on "nocarrier" in /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
            result = self._execute_script('echo 1 | sudo tee /sys/class/nfb/nfb0/net/nfb0p0/nocarrier')
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

        super()._post_test(act_test_data)


    def _test(self, act_test_data):
        """Test procedures executed for every test case.

        Overrides super()._test().

        For every ping command case (IPv4 and IPv6) ARP/ND is handled first, than ping
        commands are executed. Result depends on result of ping command.

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

        # ping device emulated on STC
        self._logger.info('    Testing response for ping...')

        self._logger.info(act_test_data.ping_command)
        output = subprocess.run(act_test_data.ping_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
        self._logger.info(output.stdout)
        if output.returncode == 0:
            self._test_result_success(act_test_data.case_name)
        else:
            self._test_result_fail(act_test_data.case_name, 'Device did not respond for the ping.')
            return
