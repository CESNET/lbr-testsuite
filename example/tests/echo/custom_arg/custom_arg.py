"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Simple example echo test with custom arguments usage.

    Custom argument has to be set within the test-runner executing this test.
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
    self.hello_msg = None

TestCaseData.init_test_specific_properties = _init_hello_test_case_data


# ----------------------------------------------------------------------
#    HELLO TEST CLASS
# ----------------------------------------------------------------------
class Custom_arg(BaseTest):

    def _set_test_cases(self):
        # Print a hello message
        hello1 = TestCaseData()
        hello1.test_name = "Echo test - custom argument."
        hello1.hello_msg = '->->->  Your custom string is: {} <-<-<-'.format(self._args.custom)
        self._add_testcase(hello1)


    def _test(self, act_test_data):
        self._logger.info('    Running an echo command...')
        output = subprocess.run('echo "' + act_test_data.hello_msg + '"', stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', shell=True)
        self._logger.info(output.stdout)

        if output.returncode == 0:
            self._test_result_success(act_test_data.test_name)
        else:
            self._test_result_fail(act_test_data.test_name, 'echo command failed.')
            return
