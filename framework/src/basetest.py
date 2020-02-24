"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala, Ivan Hazucha)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Base implementation of testing class.

    This base test class provides a common frame for all tests.
"""

import fileinput
import csv
import datetime
import inspect
import os
import re
import signal
import subprocess

from .logger import Logger
from .testresult import TestResult


CSV_COLUMN_DELIMITER=' '


class BaseTest:

    TEST_CASE_CONFIG_DIR = 'config'
    TEST_CASE_SRC_DIR = 'src'
    PROLOGUE_SETUP_FILE = 'setup.sh'
    EPILOGUE_CLEANUP_FILE = 'cleanup.sh'


    def __init__(self, args, output_dir, logger=None):
        self._args = args
        self._output_dir = output_dir
        self._apps_logs_dir = self._output_dir + '/apps-logs'
        self._test_cases = []         # Test cases setup
        self._dirs: dict = None       # List of testing environment directories
        self._logger = logger         # Logging facility
        self._base_class_logging = True
        self._results = TestResult()  # Test results object


    def run(self):
        """
        Run test as a sequence of steps defined below.
        :return: TestResult object that contains tests results data.
        """
        try:
            self._setup()
            self._prologue()
            self._testing()
            self._epilogue()
        except ConnectionRefusedError as e: # for Spirent tests
            # self._set_status(False, str(e))
            self._logger.error(e)
            self._epilogue()
        ## Add another test-specific exceptions here
        except KeyboardInterrupt:
            # self._set_status(False, 'Interrupted by SIGINT')
            self._logger.warning('Interrupted by SIGINT')
            self._epilogue()
        except Exception as e:
            # self._set_status(False, str(e))
            self._logger.error(e)
            self._epilogue()
            raise

        return self._results


    def _setup(self):
        """
        Creates output directory, seth paths to requed directories into variable _dirs.
        Also it sets up logger and initializes creation of TestCaseData objects.
        """
        test_dir = self._get_test_dir()
        self._dirs = {
            'output': os.path.join(os.getcwd(), self._output_dir),
            'apps_logs': os.path.join(os.getcwd(), self._apps_logs_dir),

            'test': test_dir,
            'config': os.path.join(test_dir, self.TEST_CASE_CONFIG_DIR),
            'src': os.path.join(test_dir, self.TEST_CASE_SRC_DIR),
        }

        self.create_dir(self._dirs['output'])
        self.create_dir(self._dirs['apps_logs'])

        self._set_logger()
        self._set_test_cases()


    # -----------------------------------------------------------------------
    # TEST EXECUTION
    # -----------------------------------------------------------------------

    def _prologue(self):
        """
        Prepare local enviroment via specified commands and setup script.
        """
        if self._base_class_logging:
            self._logger.info('Setting up local enviroment ...')

        setup_script = os.path.join(self._dirs['src'], self.PROLOGUE_SETUP_FILE)
        output = self.execute_script(setup_script)
        self._log_subprocess_output(output, "Setup script failed.", exit_on_fail=True)


    def _epilogue(self):
        """
        Cleans local enviroment via specified commands and cleaup script.
        """
        if self._base_class_logging:
            self._logger.info('Cleaning up local enviroment ...')

        cleanup_script = os.path.join(self._dirs['src'], self.EPILOGUE_CLEANUP_FILE)
        output = self.execute_script(cleanup_script)
        self._log_subprocess_output(output, "Cleanup script failed.", exit_on_fail=True)


    def _testing(self):
        """
        Executes testing phase for each TestCaseData object stored in _test_cases variable.
        """
        for case_data in self._test_cases:
            self._pre_test(case_data)
            self._test(case_data)
            self._post_test(case_data)


    def _set_test_cases(self):
        """
        Prepares testing cases. Should create array of TestCaseData objects and store it into
        _test_cases variable.
        """
        self._test_cases = [None]


    def _pre_test(self, test_case_data):
        """
        Procedures executed before every test case.
        :param test_case_data: TestCaseData object that represents particular test case.
        """
        pass


    def _test(self, test_case_data):
        """
        Test procedures executed for every test case (the test itself). This function should
        call one of test_result_success, test_result_fail or test_result_skip functions based
        on a test case result evaliatuion.
        :param test_case_data: TestCaseData object that represents particular test case.
        """
        pass


    def _post_test(self, test_case_data):
        """
        Procedures executed after every test case.
        :param test_case_data: TestCaseData object that represents particular test case.
        """
        pass


    def test_start(self, test_name):
        """
        Log test case start and increment test case counter in TestResult object.
        :param test_name: Name of the test case.
        """
        if self._base_class_logging:
            self._logger.info("\n====================================================================================")
            self._logger.info("== {} ==\n".format(test_name))
        self._results.increment_cnt()


    def test_result_skip(self, test_name, message):
        """
        Log test case result (skipped) and store the result in TestResult object.
        :param test_name: Name of the test case.
        :param message: Error message (should specify why the test case is skipped)
        """
        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: SKIPPED  --")
            self._logger.info("-- Reason: {}".format(message))
            self._logger.info("--------------------------------\n")
        self._results.add_skipped(test_name, message)


    def test_result_fail(self, test_name, message):
        """
        Log test case result (failed) and store the result in TestResult object.
        :param test_name: Name of the test case
        :param message: Error message (should specify why the test case failed)
        """
        # self._set_status(False, "FAILED - Test case: '{}'".format(test_name))
        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: FAILED   --")
            self._logger.info("-- Reason: {}".format(message))
            self._logger.info("--------------------------------\n")
        self._results.add_failed(test_name, message)


    def test_result_success(self, test_name):
        """
        Log test case result (succeeded) and store the result in TestResult object.
        :param test_name: Name of the test case.
        """
        if self._base_class_logging:
            self._logger.info("\n--------------------------------")
            self._logger.info("-- Test case result: SUCCESS  --")
            self._logger.info("--------------------------------\n")
        self._results.add_passed(test_name)


    # -----------------------------------------------------------------------
    # SET & GET METHODS
    # -----------------------------------------------------------------------

    def _get_test_dir(self):
        """
        Get test directory based on a test class source file.
        """
        test_file_path = inspect.getfile(self.__class__)
        test_dir_path = os.path.split(test_file_path)[0]
        return test_dir_path


    def _set_logger(self):
        """
        If no logger was passed to this class setup a logger to log to the log file and standard output.
        """
        if self._logger is None:
            logger = Logger(self.__class__.__name__, self._output_dir)
            self._logger = logger.create_logger()


    def add_testcase(self, test_case):
        """
        Add an test case for execution.
        :param test_case: TestData object holding test case setup.
        """
        self._test_cases.append(test_case)


    def turn_off_base_class_logging(self):
        """
        Turn of logging messages in this base class (e.g. if some child class wants to have full
        control of logging messages).
        """
        self._base_class_logging = False


    # -----------------------------------------------------------------------
    # SUBPROCESS METHODS
    # -----------------------------------------------------------------------

    @staticmethod
    def execute_script(script, args='', to=None):
        """
        Execute script with given arguments and return subprocess result object.
        :param script: Command that will be executed.
        :param args: Command arguments.
        :param to: Command timeout.
        :return: Result object of subprocess.run method.
        """
        shell_command = '{} {}'.format(script, args)
        return subprocess.run(
                shell_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8',shell=True, timeout=to)


    def _log_subprocess_output(self, output: subprocess.CompletedProcess, custom='', exit_on_fail=False):
        """
        Check subprocess.run result object exit code. In case of file log subprocess output.
        :param output: subprocess.CompletedProcess object.
        :param custom: Custom message prefix.
        :param exit_on_fail: Flag whether terminate (i.e. re-raise an exception) on command
        failure (True) or not (False).
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

            if exit_on_fail == True:
                raise


    # -----------------------------------------------------------------------
    # CSV METHODS
    # -----------------------------------------------------------------------

    @staticmethod
    def store_data_as_csv(file: str, data: list):
        """
        Stores data into file in CSV format.
        :param file: Name of file where date will be stored.
        :param data: Data that will be stored in file.
        """
        with open(file, 'a') as csvfile:
            writer = csv.writer(
                csvfile, delimiter=CSV_COLUMN_DELIMITER,
                quotechar='|', quoting=csv.QUOTE_MINIMAL
            )
            writer.writerow(data)


    @staticmethod
    def get_csv_column_by_name(file: str, name: str, output_type: type = str) -> list:
        """
        Get lis of values from column specified by name.
        :param file: Name of the CSV file.
        :param name: Name of a column.
        :param output_type: Type of data that will be returned (default string).
        :return: List of values of specified type from specified file and column.
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
        """
        Get lis of values from column specified by index.
        :param file: Name of the CSV file.
        :param index: Index of a column.
        :param output_type: Type of data that will be returned (default tring).
        :return: List of values of specified type from specified file and column.
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
    def create_dir(name):
        """
        Creates directory wit specified name.
        """
        if not os.path.exists(name):
            os.mkdir(name)


    def _get_csv_file_path(self, file_name):
        """
        Return path to specified file in output directory.
        :param file_name: Name of the file.
        :return: Path to specified file in the directory.
        """
        return os.path.join(self._output_dir, file_name)


    def _get_config_file_path(self, file_name):
        """
        Return path to specified file in config directory of particular test.
        :param file_name: Name of a file.
        :return: Path to specified file in the directory.
        """
        return os.path.join(self._dirs['test'], self.TEST_CASE_CONFIG_DIR, file_name)


    def add_test_result_pdf(self, pdf_file_name): # test_result_add_pdf -> add_test_result_pdf
        """
        Add pdf file name, that will be included in HTML document with tests results.
        :param pdf_file_name: Name of PDF file.
        """
        self._results.add_pdf_file(pdf_file_name)
