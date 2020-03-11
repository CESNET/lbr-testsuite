"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala, Ivan Hazucha)
Copytight: (C) 202O CESNET
License: GPL-2.0

Simple example echo test.

This test only prints a configured text using echo command. If echo command
finishes successfully the test passes, otherwise it failes.
"""

import os
import sys
import subprocess

# Appends PYTHONPATH to enable tests framework modules access
sys.path.append(os.path.abspath(__file__ + "/../../../../.."))
from framework import BaseTest, TestCaseData


# ----------------------------------------------------------------------
#    TEST CASE DATA CLASS PREPARATION
# ----------------------------------------------------------------------
def _init_hello_test_case_data():
    """Initialization of custom test case data properties.

    Overrides TestCaseData._init_hello_test_case_data)) method.
    """

    self.hello_msg = None

TestCaseData.init_test_specific_properties = _init_hello_test_case_data


# ----------------------------------------------------------------------
#    HELLO TEST CLASS
# ----------------------------------------------------------------------
class Hello(BaseTest):
    """ Class of the Hello test.

    Extends BaseTest class by overriding methods for test cases setup and
    test body.
    """

    def _set_test_cases(self):
        """Set test cases

        Method prepares single test case with an example test text.
        """

        hello1 = TestCaseData()
        hello1.test_name = "Echo test - hello."
        hello1.hello_msg = '->->->  Hello, I am an example test. <-<-<-'
        self._add_testcase(hello1)


    def _test(self, act_test_data):
        """Execute the test for every configured test case.

        For every configured test case run "echo" command and check its return value.
        """

        self._logger.info('    Running an echo command...')
        output = subprocess.run('echo "' + act_test_data.hello_msg + '"', stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, encoding='utf-8', shell=True)
        self._logger.info(output.stdout)

        if output.returncode == 0:
            self._test_result_success(act_test_data.test_name)
        else:
            self._test_result_fail(act_test_data.test_name, 'echo command failed.')
            return
