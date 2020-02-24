"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Class for tests executing.

    This class is responsible for test execution. It runs all selected tests (all configured by
    default) and provides information about progress and test results. Test results are presented
    in a text form on standard output and in a log file and as a html summary page.
"""

import datetime
import fnmatch
import importlib
import os
import socket    # hostname
import sys

sys.path.append(os.path.abspath(__file__ + "/.."))

from src.arguments import Arguments
from src.basetest import TestResult
from src.logger import Logger
from src.resultgenerator import generate_html


# ----------------------------------------------------------------------
#     EXCEPTIONS
# ----------------------------------------------------------------------

class InvalidTestsConfigError(Exception):
    pass


class TestRunnerError(Exception):
    pass


# ----------------------------------------------------------------------
#     TESTRUNNER
# ----------------------------------------------------------------------

class TestRunner:

    TEST_CONFIG_FILE = 'tests.json'

    def __init__(self, arguments, output_dir, supported_tests, tests_dir):
        """
        Initialize test runner.
        :param arguments: Parsed command line arguments.
        :param output_dir: Absolute path to output_dir.
        :param supported_tests: List of supported tests (reflecting directory hierarchy in tests_dir).
        :param tests_dir: Location of tests directory (absolute path).
        """
        if not os.path.isabs(output_dir):
            raise ValueError("Output directory \"{}\" has to be absolute, not relative.". format(output_dir))

        if not os.path.isabs(tests_dir):
            raise ValueError("Tests directory \"{}\" has to be absolute, not relative.". format(tests_dir))

        self._args = arguments
        self._output_dir = output_dir
        self._logger = None
        # Set up via config file:
        self._supported_tests = supported_tests
        self._tests_dir = tests_dir


    def run(self):
        """
        Run all test cases for all tests clases specified in the _supported_tests file, optionaly
        selected / restricted via arguments (include / exclude).
        :return: True if all test cases passed, else False
        """
        tests = self._select_tests(self._args.include, self._args.exclude)

        logger = Logger(self.__class__.__name__, self._output_dir)
        self._logger = logger.create_logger()

        self.print_setup_info()
        self.print_tests_info(tests)

        start_time = datetime.datetime.now()

        # Run selected tests
        results = []
        for test in tests:
            results.append([test, self._run_test(test)])

        generate_html(results, str(start_time), self._calculate_duration(start_time), self._output_dir)

        total_results = self._log_total_summary(results)

        return total_results.failed_cnt == 0


    def _run_test(self, test: str):
        """
        Execute all tests in specified class.
        :param test: Name of test class.
        :return: TestResult object that contains tests results data.
        """
        test_class = self._get_test_class(test)

        test_object = test_class(self._args, self._output_dir, self._logger)
        result = test_object.run()

        return result


    def _get_test_class(self, test_name):
        """
        Gets test class specified by name.
        :param test_name: Name of test class.
        :return: Requested test class.
        """
        assert os.path.isabs(self._tests_dir), "Test directory has to be absolute, not relative."
        # Get test module based on provided tests folder and test name
        act_test_module_name = test_name.split(os.path.sep)[-1]

        act_test_dir = os.path.abspath(os.path.join(self._tests_dir, test_name))
        sys.path.append(act_test_dir)

        act_test_module = importlib.import_module(act_test_module_name)

        # Return corresponding class
        return getattr(act_test_module, act_test_module_name.capitalize())


    def _select_tests(self, include, exclude):
        """
        Create list of tests for execution using list of supported tests and include / exclude
        test selectors (from arguments).
        :param include: Name of tests to include.
        :param exclude: Name of tests to exclude.
        :return: List of test for execution.
        """
        incltests = []
        for test in self._supported_tests:
            for incl in include:
                if fnmatch.fnmatch(test, incl):
                    incltests.append(test)

        excltests = []
        for test in incltests:
            skip = False
            for excl in exclude:
                if fnmatch.fnmatch(test, excl):
                    skip = True
                    break
            if skip:
                continue
            excltests.append(test)

        return excltests


    @staticmethod
    def _calculate_duration(start_time):
        """
        Calculate duration of a test from passed start time to now.
        :param start_time: Datetime from which duration should be calculated.
        :return: Duration in format hh:mm:ss.
        """
        delta = datetime.datetime.now() - start_time
        total_seconds = delta.seconds
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


# ----------------------------------------------------------------------
#     PRINT FUNCTIONS
# ----------------------------------------------------------------------

    def print_setup_info(self):
        """
        Print information about general setup.
        """
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("| Testsuite -> START                                            |")
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("TEST SETUP:")
        self._logger.info("    Testsuite run on server          : {}".format(socket.gethostname()))
        self._logger.info("    Output directory                 : {}".format(self._output_dir))
        self._logger.info("    Supported tests                  : {}".format(self._supported_tests))
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("|                                                               |")
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


    def print_tests_info(self, tests):
        """
        Print information about tests to run.
        :param tests: List of names of tests to ŕun.
        """
        self._logger.info("TEST CASES:")
        for test in tests:
            self._logger.info("    {}".format(test))
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("|                                                               |")
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("<                                                               >")
        self._logger.info("<                        RUNNING TESTS                          >")
        self._logger.info("<                                                               >")
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


    def _log_total_summary(self, results):
        """
        Print and return summary statistics from all run test cases.
        :param results: List of results from individual test cases.
        :return: Summary from all run tests.
        """
        summary = TestResult()
        for result in results:
            summary.test_cnt += result[1].test_cnt
            summary.passed_cnt += result[1].passed_cnt
            summary.failed_cnt += result[1].failed_cnt
            summary.skipped_cnt += result[1].skipped_cnt

        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        self._logger.info("TOTAL RESULTS: RAN: {}, PASSED: {}, FAILED: {}, SKIPPED: {}".format(
                    summary.test_cnt, summary.passed_cnt, summary.failed_cnt, summary.skipped_cnt))
        self._logger.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

        return summary
