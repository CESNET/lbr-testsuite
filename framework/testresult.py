"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala)
Copytight: (C) 202O CESNET
License: GPL-2.0

Test result module provides simple class for storing results from all test cases
execution and for final report generation.
"""


class TestResult:
    """Class for unified test results storage and reporting.

    Attributes
    ----------
    test_cnt : int
        Count of total test cases run.
    passed_cnt : int
        Count of passed test cases (i.e. test cases finished with success).
    failed_cnt : int
        Count of failed test cases.
    skipped_cnt : int
        Count of skipped test cases. A test case is skipped when it makes no sense to run the case.
    test_results : list({'case_name', 'result', 'message'})
        List of test result dictionaries containing case names succes/fail/skip result
        keyword and test case result message. Only skipped and failed tests contains a case
        result message.
    pdf_files : list(str)
        List of output pdf files.

    Methods
    -------
    increment_cnt()
        Increment total count of test cases run.
    add_passed(case_name)
        Adds passed test case result.
    add_failed(case_name)
        Adds passed test case result.
    add_skipped(case_name)
        Adds passed test case result.
    add_output_pdf_file(pdf_file_name)
        Add an output pdf file.
    """

    def __init__(self):
        self.test_cnt = 0
        self.passed_cnt = 0
        self.failed_cnt = 0
        self.skipped_cnt = 0
        self.test_results = []
        self.pdf_files = []


    def increment_cnt(self):
        """Increment total count of test cases run.
        """

        self.test_cnt += 1


    def add_passed(self, case_name):
        """Add passed test case to the test results.

        Parameters
        ----------
        case_name : str
            Name of the passed test case.
        """

        self.test_results.append({'case_name': case_name, 'result': 'success', 'message':''})
        self.passed_cnt += 1


    def add_failed(self, case_name, result_message):
        """Add failed test case to the test results.

        Parameters
        ----------
        case_name : str
            Name of the passed test case.
        result_message : str
            Test case result message (i.e reason why test failed).
        """

        self.test_results.append({'case_name': case_name, 'result': 'fail', 'message': result_message})
        self.failed_cnt += 1


    def add_skipped(self, case_name, result_message):
        """Add skipped test case to the test results.

        Parameters
        ----------
        case_name : str
            Name of the passed test case.
        result_message : str
            Test case result message (i.e reason why the test has been skipped).
        """

        self.test_results.append({'case_name': case_name, 'result': 'skip', 'message': result_message})
        self.skipped_cnt += 1


    def add_output_pdf_file(self, pdf_file_name):
        """Add an output pdf file to the list of pdf files.

        Parameters
        ----------
        pdf_file_name : str
            Name of the file
        """

        self.pdf_files.append(pdf_file_name)