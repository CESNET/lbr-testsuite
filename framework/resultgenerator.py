"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala)
Copytight: (C) 202O CESNET
License: GPL-2.0

This module is used for generating HTML document with test results report.

This module requires shutil and yattag packages.

Functions
---------
generate_html(test_results, start_time, duration, output_dir)
    Generates a test results HTML page.
"""

import os
import socket

from shutil import copyfile
from yattag import Doc

""" Name of the test results page """
HTML_RESULTS_FILENAME = 'testresults.html'


# ----------------------------------------------------------------------
#     PRIVATE AUXILIARY FUNCTIONS
# ---------------------------------------------------------------------.

def _sum_all_passed(test_results):
    """ Count all passed test cases.

    Parameters
    ----------
    test_results : TestResult
        TestResult objects containing results from all run tests.

    Returns
    -------
    int
        Count of all passed tests.
    """

    sum = 0
    for test_result in test_results:
        sum += test_result[1].passed_cnt
    return sum


def _sum_all_failed(test_results):
    """ Count all failed test cases.

    Parameters
    ----------
    test_results : TestResult
        TestResult objects containing results from all run tests.

    Returns
    -------
    int
        Count of all failed tests.
    """

    sum = 0
    for test_result in test_results:
        sum += test_result[1].failed_cnt
    return sum


def _sum_all_skipped(test_results):
    """ Count all skipped test cases.

    Parameters
    ----------
    test_results : TestResult
        TestResult objects containing results from all run tests.

    Returns
    -------
    int
        Count of all skipped tests.
    """

    sum = 0
    for test_result in test_results:
        sum += test_result[1].skipped_cnt
    return sum


def _sum_all_executed(test_results):
    """ Count all executed test cases.

    Parameters
    ----------
    test_results : TestResult
        TestResult objects containing results from all run tests.

    Returns
    -------
    int
        Count of all executed tests.
    """

    sum = 0
    for test_result in test_results:
        sum += test_result[1].test_cnt
    return sum


def _get_java_script():
    """ Create short script used in created HTML document.

    TODO co ten skript dela...

    Returns
    -------
    str
        Created java script.
    """

    java_script = \
            '<script src="script.js"></script>' \
            '<script type="text/javascript">' \
            '$(document).ready(function(){' \
            '$(\'td\').on(\'click\', \'.btn\', function(e){' \
            'e.preventDefault();' \
            'var $this = $(this);' \
            'var $nextRow = $this.closest(\'tr\').next(\'tr\');' \
            '$nextRow.slideToggle("fast");' \
            '$this.text(function(i, text){' \
            'if (text === \'View\') {' \
            ' return \'Hide\';' \
            '} else {' \
            'return \'View\';' \
            '};' \
            '});' \
            '});' \
            '});' \
            '</script>'

    return java_script


# ----------------------------------------------------------------------
#     PUBLIC FUNCTION FOR GENERATING RESULTS HTML PAGE
# ----------------------------------------------------------------------

def generate_html(test_results, start_time, duration, output_dir):
    """ Generates HTML page using passed test results and prepared formating files (script.js and
    bootstrap.css).

    Generated HTML page is stored inside the passed output directory (together with copy
    of script.js and bootstrap.css files).

    TODO popis stranky

    Parameters
    ----------
    test_results : TestResult
        TestResult objects containing results from all run tests.
    start_time : str
        Start time of a test run as a string representation of local date and time.
    duration :
        String representation of the test duration.
    output_dir : str
        Path to the output directory where HTML results page should be stored.
    """

    doc, tag, text = Doc().tagtext()

    with tag('html'):
        with tag('head'):
            doc.asis('<meta charset="utf-8">')
            doc.asis('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
            doc.asis('<link rel="stylesheet" href="bootstrap.css">')
        with tag('body'):
            with tag('div', klass="container"):
                with tag('div', klass="row"):
                    with tag('div', klass="col-xs-6"):
                        with tag('p'):
                            with tag('strong'):
                                text("Executed on server: ")
                            text(socket.gethostname())
                        with tag('p'):
                            with tag('strong'):
                                text("Start Time: ")
                            text(start_time)
                        with tag('p'):
                            with tag('strong'):
                                text("Duration: ")
                            text(duration)
                        with tag('p'):
                            with tag('strong'):
                                text("Status: ")
                            if _sum_all_failed(test_results) <= 0:
                                text('SUCCESS')
                            else:
                                text("FAIL")
                    with tag('div', klass="col-xs-6"):
                        with tag('p'):
                            with tag('strong'):
                                text('TOTAL RESULTS')
                        with tag('p'):
                            with tag('strong'):
                                text('RAN: ')
                            text(_sum_all_executed(test_results))
                        with tag('p'):
                            with tag('strong'):
                                text('PASSED: '.format(_sum_all_passed(test_results)))
                            text(_sum_all_passed(test_results))
                        with tag('p'):
                            with tag('strong'):
                                text('FAILED :')
                            text(_sum_all_failed(test_results))
                        with tag('p'):
                            with tag('strong'):
                                text('SKIPPED: '.format(_sum_all_skipped(test_results)))
                            text(_sum_all_skipped(test_results))
                with tag('div', klass="row"):
                    with tag('div', klass="col-xs-15 col-sm-10 col-md-10"):
                        with tag('table', klass="table table-hover table-responsive"):
                            with tag('thead'):
                                with tag('tr'):
                                    with tag('th'):
                                        text('Test Case')
                                    with tag('th'):
                                        text('Status')
                            with tag('tbody'):
                                for test_result in test_results:
                                    # test_result[0] = name of test class (e.g.: watchdog/maceditor/...)
                                    # test_result[1] = TestResult object
                                    with tag('td', klass="col-xs-12"):
                                        text(test_result[0])
                                    for test_case in test_result[1].test_results:
                                        # test_case['case_name'] = test case name
                                        # test_case['result'] = test case result: success/fail/skip)
                                        # test_case['message'] = test case error message (in case of result is fail/skip)
                                        with tag('tr', klass='{}'.format(test_case['result'])):
                                            with tag('td', klass="col-xs-12"):
                                                text(test_case['case_name'])
                                            with tag('td', klass="col-xs-3 text-center"):
                                                with tag('span', klass='label label-{}'.format(test_case['result'])):
                                                    if test_case['result'] == "success":
                                                        text("Pass")
                                                    elif test_case['result'] == "skip":
                                                        text("Skip")
                                                    elif test_case['result'] == "fail":
                                                        text("Fail")
                                                    else:
                                                        text("Error")
                                            with tag('td', klass="col-xs-3 text-center"):
                                                if test_case['result'] != "success":
                                                    doc.asis(
                                                        '&nbsp<button class="btn btn-default btn-xs">View</button>')
                                        with tag('tr', style="display:none;"):
                                            with tag('td', klass="col-xs-9"):
                                                with tag('p'):
                                                    text(test_case['message'])
                                    if len(test_result[1].pdf_files) is not 0:
                                        for file_name in test_result[1].pdf_files:
                                            status = 'success' if test_result[1].failed_cnt == 0 else "fail"
                                            with tag('tr', klass='{}'.format(status)):
                                                with tag('td'):
                                                    doc.asis('<embed src="{}#view=FitV" width="100%" height ="550px">'.format(file_name))

            doc.asis(_get_java_script())

    html_doc = doc.getvalue()

    with open(output_dir + '/' + HTML_RESULTS_FILENAME, "w") as text_file:
            text_file.write(html_doc)

    script_file = os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + '/script.js')
    bootstrap_file = os.path.normpath(os.path.dirname(os.path.realpath(__file__)) + '/bootstrap.css')

    copyfile(script_file, output_dir + '/script.js')
    copyfile(bootstrap_file, output_dir + '/bootstrap.css')
