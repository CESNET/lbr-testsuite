"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala)
Copytight: (C) 202O CESNET
License: GPL-2.0

This module provides a class for tests execution.

The TestRunner class runs all selected tests (by default all configured) and provides
information about progress and summary test results report. Test results are presented
in a text form on standard output and in a log file and as a html summary page.
"""

import datetime
import fnmatch
import importlib
import os
import socket    # hostname
import sys


from .arguments import Arguments
from .basetest import TestResult
from .logger import Logger
from .resultgenerator import generate_html


# ----------------------------------------------------------------------
#     TESTRUNNER
# ----------------------------------------------------------------------

class TestRunner:
    """Class for tests execution.

    This class is configured on creation. After successfull creation all tests are executed
    using run() method.

    Attributes
    ----------
    _args : ArgumentParser.parseargs() populated namespace
        Set of program arguments.
    _output_dir : str
        Path to the output directory where test outputs will be stored.
    _apps_logs_dir: str
        Path to the directory where apllication specific logs (if any) will be stored.
        It is common for this directory to be an _output_dir subdicrectory.
    _logger: logging.Logger
        Logging facility object.
    _supported tests : list
        List of supported tests.
    _tests_dir : str
        Absolute path to the tests directory.

    Methods
    -------
    run()
        Run all selected tests and generate results.
    """

    def __init__(self, arguments, output_dir, supported_tests, tests_dir):
        """
        Parameters
        ----------
        arguments : ArgumentParser.parseargs() populated namespace
            Set of parsed arguments.
        output_dir : str
            Absolute path to the output directory where test outputs will be stored.
        supported_tests : list(str)
            List of supported tests (reflecting directory hierarchy in tests_dir).
        tests_dir : str
            Location of tests directory (absolute path).
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
        """Run all selected test cases.

        Runall tests clases specified in the _supported_tests list, optionaly
        selected / restricted via arguments (include / exclude).

        Returns
        -------
        bool
            True if all test cases passed, False otherwise.
        """

        # Select tests to run using _supported_tests list and include / exclude arguments
        tests = self._select_tests()

        # Set up logger
        logger = Logger(self.__class__.__name__, self._output_dir)
        self._logger = logger.create_logger()

        self._print_setup_info()
        self._print_tests_info(tests)

        start_time = datetime.datetime.now()

        # Run all selected tests, store its results
        results = []
        for test in tests:
            results.append([test, self._run_test(test)])

        # Generate final report in HTML format
        generate_html(results, str(start_time), self._calculate_duration(start_time), self._output_dir)

        # Get and log results summary
        total_results = self._log_total_summary(results)

        return total_results.failed_cnt == 0


    def _select_tests(self):
        """Create list of tests for execution.

        List of test for execution is created using list of supported tests from the tests
        configuration and include / exclude test selectors (from arguments).

        Returns
        -------
        list(str)
            List of tests for execution.
        """

        incltests = []
        for test in self._supported_tests:
            for incl in self._args.include:
                if fnmatch.fnmatch(test, incl):
                    incltests.append(test)

        selected_tests = []
        for test in incltests:
            exclude = False
            for excl in self._args.exclude:
                if fnmatch.fnmatch(test, excl):
                    exclude = True
                    break
            if not exclude:
                selected_tests.append(test)

        return selected_tests


    def _run_test(self, test: str):
        """Execute a selected test.

        Parameters
        ----------
        test : str
            Test name selector (path from the tests configuration).

        Returns
        -------
        TestResult
            Test result object that contains results from all executed test cases.
        """

        test_class = self._get_test_class(test)

        test_object = test_class(self._args, self._output_dir, self._logger)
        result = test_object.run()

        return result


    def _get_test_class(self, test_name):
        """Import test class specified by its name (path).

        Parameters
        ----------
        test_name : str
            Name of test class (path relative the tests directory).

        Returns
        -------
        class
            Requested imported test class object.
        """

        assert os.path.isabs(self._tests_dir), "Test directory has to be absolute, not relative."
        # Get test module based on provided tests folder and test name
        act_test_module_name = test_name.split(os.path.sep)[-1]

        act_test_dir = os.path.abspath(os.path.join(self._tests_dir, test_name))
        sys.path.append(act_test_dir)

        act_test_module = importlib.import_module(act_test_module_name)

        # Return corresponding class
        return getattr(act_test_module, act_test_module_name.capitalize())


    @staticmethod
    def _calculate_duration(start_time):
        """Calculate duration of a test.

        The duration is calculated from start time passed via argument to acutla time.

        Parameters
        ----------
        start_time : datetime.datetime
            Date and time of test start.

        Returns
        -------
        str
            Test duration in format hh:mm:ss.
        """

        delta = datetime.datetime.now() - start_time
        total_seconds = delta.seconds
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


# ----------------------------------------------------------------------
#     PRINT FUNCTIONS
# ----------------------------------------------------------------------

    def _print_setup_info(self):
        """Print information about general setup
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


    def _print_tests_info(self, tests):
        """Print information about tests to run.

        Parameters
        ----------
        tests : list
            List of names of tests to ŕun.
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
        """Print and return summary statistics from all run test cases.

        Parameters
        ----------
        results : list(TestResult)
            List of results from all executed tests.

        Returns
        -------
        TestResult
            Test result object containing summary information from all passed results.
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
