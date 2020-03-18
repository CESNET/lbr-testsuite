"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala, Ivan Hazucha)
Copytight: (C) 202O CESNET
License: GPL-2.0

Base test module. Provides a common frame for all tests. Specific tests should be
created as subclasses of thís base class.
"""

import csv
import datetime
import fileinput
import inspect
import os
import re
import signal
import subprocess

from .logger import Logger
from .testresult import TestResult


CSV_COLUMN_DELIMITER=' '


class BaseTest:
    """Base test class providing frame for a test execution.

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
    _results : TestReult
        Test results object for storing results from tests execution.
    _test_cases: list(TestCaseData)
        Setup of all test cases from within a test.
    _dirs: dict
        Dictionary of test internal directores - output, application(s) output, tests source,
        tests configuration and test sources directories.
    _base_class_logging: bool
        Flag wheter logging outputs from this class are allowed or not. Default to True.
        Set this to False if all logging outputs needs to be handled from subclass only.

    Methods
    -------
    run()
        Run all test cases.
    """

    _TEST_CASE_CONFIG_DIR = 'config'
    _TEST_CASE_SRC_DIR = 'src'
    _PROLOGUE_SETUP_FILE = 'setup.sh'
    _EPILOGUE_CLEANUP_FILE = 'cleanup.sh'

    def __init__(self, args, output_dir, logger=None):
        """
        Parameters
        ----------
        args : ArgumentParser.parseargs() populated namespace
            Set of parsed arguments.
        output_dir : str
            Path to the output directory where test outputs will be stored.
        logger : logging.Logger, optional
            Initialized logging facility object. If a logger is not passed, it is
            created later in the _setup() method.
        """

        self._args = args
        self._output_dir = output_dir
        self._apps_logs_dir = self._output_dir + '/apps-logs'
        self._logger = logger
        self._dirs: dict = None
        self._base_class_logging = True
        self._test_cases = []
        self._results = TestResult()


    def run(self):
        """Run test as a sequence of steps defined below.

        Returns
        -------
        TestResult
            TestResult objects containing results from all executed tests.
        """

        try:
            self._setup()
            self._prologue()
            self._testing()
            self._epilogue()
        except KeyboardInterrupt:
            self._logger.warning('Interrupted by SIGINT')
            self._epilogue()
        ## Add another test-specific exceptions here
        except Exception as e:
            self._logger.error(e)
            self._epilogue()
            raise

        return self._results


    def _setup(self):
        """Perform general test environment setup.

        Creates directories for outputs, sets paths to test directories in list
        _dirs, sets up logger (if no logger has been passed via constructor) and
        calls method for setting up of all test cases (the implementation should be
        provided within a particular test implementation).
        """

        # Get a path to a directory where tests implementation is located.
        test_dir = self._get_test_dir()
        # Set internal directories
        self._dirs = {
            # Test outputs
            'output': os.path.join(os.getcwd(), self._output_dir),
            # Location for important outputs of application(s) run during a test
            'apps_logs': os.path.join(os.getcwd(), self._apps_logs_dir),
            # Location of test classes implementation
            'test': test_dir,
            # Location of test configuration
            'config': os.path.join(test_dir, self._TEST_CASE_CONFIG_DIR),
            # Location of test auxiliary scripts
            'src': os.path.join(test_dir, self._TEST_CASE_SRC_DIR),
        }

        # Create dirs if not exists
        self._create_dir(self._dirs['output'])
        self._create_dir(self._dirs['apps_logs'])

        self._set_logger()
        self._set_test_cases()


    # -----------------------------------------------------------------------
    # TEST EXECUTION
    # -----------------------------------------------------------------------

    def _prologue(self):
        """Perform environment preparation common for all test cases within a test.

        Environment preparation is done through commands placed inside this method
        and via setup script placed in the test auxiliary scripts directory.
        """

        if self._base_class_logging:
            self._logger.info('Setting up local enviroment ...')

        setup_script = os.path.join(self._dirs['src'], self._PROLOGUE_SETUP_FILE)
        output = self._execute_script(setup_script)
        self._check_subprocess_output(output, "Setup script failed.", exit_on_fail=True)


    def _epilogue(self):
        """Clean up environment set up common for all test cases within a test.

        Cleanup is done through commands placed inside this method and via cleanup
        script placed in the test auxiliary scripts directory. This method typicaly
        reverts commands from _prologue().
        """

        if self._base_class_logging:
            self._logger.info('Cleaning up local enviroment ...')

        cleanup_script = os.path.join(self._dirs['src'], self._EPILOGUE_CLEANUP_FILE)
        output = self._execute_script(cleanup_script)
        self._check_subprocess_output(output, "Cleanup script failed.", exit_on_fail=True)


    def _testing(self):
        """Execute testing phase for each configured test case.

        Test cases setup is stored _test_cases variable.
        """

        for case_data in self._test_cases:
            self._pre_test(case_data)
            self._test(case_data)
            self._post_test(case_data)


    def _set_test_cases(self):
        """Prepare testing cases set up.

        This method should be overriden within an implementation of a particular test. This method
        should create set up for all test cases and store it inside the _test_cases list.
        """
        self._test_cases = [None]


    def _pre_test(self, test_case_data):
        """Procedures executed before every test case.

        Parameters
        ----------
        test_case_data : TestCaseData
            Object containing test case set up.
        """

        # Log and report start of a test case
        if self._base_class_logging:
            self._logger.info("\n====================================================================================")
            self._logger.info("== {} ==\n".format(test_case_data.case_name))
        self._results.increment_cnt()


    def _test(self, test_case_data):
        """Test procedures executed for every test case.

        Implementation of this method represent the core of a test (the test itself). This
        method should call one of _test_result_success, _test_result_fail or _test_result_skip
        methods based on a test case result evaliatuion. Through these calls, results of
        all executed test cases are recorded and reported as a final test result.

        Parameters
        ----------
        test_case_data : TestCaseData
            Object containing test case set up.
        """

        pass


    def _post_test(self, test_case_data):
        """Procedures executed after every test case.

        Typicaly, this method reverts steps from _pre_test() phase.

        Parameters
        ----------
        test_case_data : TestCaseData
            Object containing test case set up.
        """

        pass


    def _test_result_success(self, test_name):
        """Log succeeded test case and store the result.

        Parameters
        ----------
        test_name : str
            Name of a test case
        """

        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: SUCCESS  --")
            self._logger.info("--------------------------------\n")
        self._results.add_passed(test_name)


    def _test_result_fail(self, test_name, message):
        """Log failed test case and store the result.

        Parameters
        ----------
        test_name : str
            Name of a test case
        message : str
            Description why the case has been skipped.
        """

        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: FAILED   --")
            self._logger.info("-- Reason: {}".format(message))
            self._logger.info("--------------------------------\n")
        self._results.add_failed(test_name, message)


    def _test_result_skip(self, test_name, message):
        """Log skipped test case and store the result.

        Parameters
        ----------
        test_name : str
            Name of a test case
        message : str
            Description why the case has been skipped.
        """

        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: SKIPPED  --")
            self._logger.info("-- Reason: {}".format(message))
            self._logger.info("--------------------------------\n")
        self._results.add_skipped(test_name, message)


    # -----------------------------------------------------------------------
    # SET & GET METHODS
    # -----------------------------------------------------------------------

    def _get_test_dir(self):
        """Get test directory based on a test class source file.

        Returns
        -------
        str
            Path to the test directory.
        """

        test_file_path = inspect.getfile(self.__class__)
        test_dir_path = os.path.split(test_file_path)[0]
        return test_dir_path


    def _set_logger(self):
        """Setup a logger if no logger was passed to this class.

        The logger is set to log to the log file and standard output.
        """

        if self._logger is None:
            logger = Logger(self.__class__.__name__, self._output_dir)
            self._logger = logger.create_logger()


    def _add_testcase(self, test_case):
        """Add a test case for execution.

        Parameters
        ----------
        test_case : TestCaseData
            Test case data object holding test case setup.
        """

        self._test_cases.append(test_case)


    def _turn_off_base_class_logging(self):
        """Turn of logging messages in this base class.

        Use this if some child class wants to have full control over logging messages.
        """

        self._base_class_logging = False


    # -----------------------------------------------------------------------
    # SUBPROCESS METHODS
    # -----------------------------------------------------------------------

    @staticmethod
    def _execute_script(script, args='', timeout=None):
        """Execute script with given arguments and return subprocess result object.

        Parameters
        ----------
        script : str
            Command that will be executed.
        args : str, optional
            Command arguments (default is empty string, i.e. no arguments).
        timeout : int, optional
            Command timeout in seconds (default is no timeout).

        Returns
        -------
        subprocess.CompletedProcess
            Result object of executed command.
        """
        shell_command = '{} {}'.format(script, args)
        return subprocess.run(
                shell_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding='utf-8', shell=True, timeout=timeout)


    def _check_subprocess_output(self, output: subprocess.CompletedProcess, custom='', exit_on_fail=False):
        """Check result of command execution.

        The check is made through inspection of an instance of subprocess.CompletedProcess
        object.

        Parameters
        ----------
        output : subprocess.CompletedProcess
            An executed command result object.
        custom : str, optional
            A custom message from calling application (i.e. test implementation; default
            is an empty string).
        exit_on_fail : bool, optional
            Flag whether terminate (i.e. re-raise an exception) on command failure (True)
            or not (False) (default is False, i.e. do not terminate on failure).
        """
        try:
            merged_output = custom + output.stdout + output.stderr
            if output.check_returncode():
                if self._base_class_logging:
                    self._logger.error('\n' + merged_output)

        except Exception as e:
            self._logger.error('{}\n    {}'.format(custom, e))
            if output.stderr:
                if self._base_class_logging:
                    self._logger.error('    Returned error: {}\n'.format(output.stderr))

            if exit_on_fail:
                raise


    # -----------------------------------------------------------------------
    # CSV METHODS
    # -----------------------------------------------------------------------

    @staticmethod
    def store_data_row_as_csv(file: str, data_row: list):
        """Store data into a file in CSV format.

        Parameters
        ----------
        file : str
            Name of file where date will be stored.
        data_row : list
            Data row that will be stored in the CSV file.
        """
        with open(file, 'a') as csvfile:
            writer = csv.writer(
                csvfile, delimiter=CSV_COLUMN_DELIMITER,
                quotechar='|', quoting=csv.QUOTE_MINIMAL
            )
            writer.writerow(data_row)


    @staticmethod
    def get_csv_column_by_name(file: str, name: str, output_type: type = str) -> list:
        """Get values from a selected column. Column is selected by name.

        Parameters
        ----------
        file : str
            Name of file where date will be stored.
        name : str
            Name of a column.
        output_type : type
            Requested type for retrieved values.

        Returns
        -------
        list(type)
            List of values of requested type from specified file and column name.

        Raises
        ------
        KeyError
            When column of requested name is not present.
        """
        column = []

        with open(file, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=CSV_COLUMN_DELIMITER)
            for row in reader:
                if name not in row:
                    raise KeyError
                column.append(row[name])

        return [output_type(x) for x in column]


    @staticmethod
    def get_csv_column_by_index(file: str, index: int, output_type: type = str) -> list:
        """"Get values from a selected column. Column is selected by index.

        Parameters
        ----------
        file : str
            Name of file where date will be stored.
        index : int
            Index of a column.
        output_type : type
            Requested type for retrieved values.

        Returns
        -------
        list(type)
            List of values of requested type from specified file and column index.
        """
        column = []

        with open(file, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=CSV_COLUMN_DELIMITER)
            for row in reader:
                column.append(row[index])

        return [output_type(x) for x in column]


    # -----------------------------------------------------------------------
    # OTHER AUXILIARY METHODS
    # -----------------------------------------------------------------------

    @staticmethod
    def _create_dir(name):
        """Create a directory wit specified name.

        Parameters
        ----------
        name : str
            Path to the directoy to create
        """
        if not os.path.exists(name):
            os.mkdir(name)


    def _add_test_result_pdf(self, pdf_file_name):
        """Add pdf file name, that will be included in HTML document with tests results.

        TODO popsat presneji pouziti

        Parameters
        ----------
        pdf_file_name : str
            Name of the file.
        """
        self._results.add_output_pdf_file(pdf_file_name)
