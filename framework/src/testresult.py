"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Simple test result class implementation.

    Contains mandatory test result class members for unified test reults reporting.
"""


class TestResult:

    def __init__(self):
        self.test_cnt = 0        # Total test cases count
        self.passed_cnt = 0      # Passed test cases count
        self.failed_cnt = 0      # Failed test cases count
        self.skipped_cnt = 0     # Skipped test cases count
        self.pdf_files = []      # List of output pdf files
        self.test_results = []   # Test result messages. Contains case names
                                 # succes/danger/waring keyword and test case result message


    def increment_cnt(self):
        """
        Increment total count of test cases run.
        """
        self.test_cnt += 1


    def add_passed(self, case_name):
        """
        Increment total count of passed test cases.
        """
        self.test_results.append([case_name, 'success', ''])
        self.passed_cnt += 1


    def add_failed(self, case_name, case_result):
        """
        Increment total count of failed test cases.
        """
        self.test_results.append([case_name, 'danger', case_result])
        self.failed_cnt += 1


    def add_skipped(self, case_name, case_result):
        """
        Increment total count of skipped test cases.
        """
        self.test_results.append([case_name, 'warning', case_result])
        self.skipped_cnt += 1


    def add_pdf_file(self, pdf_file_name):
        """
        Add filename to the list of pdf files.
        """
        self.pdf_files.append(pdf_file_name)