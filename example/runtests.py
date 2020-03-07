"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Script for example tests execution.
"""

import os
import sys

# Appends PYTHONPATH to enable tests framework modules access
sys.path.append(os.path.abspath(__file__ + "/../.."))
from testrunner import TestRunner
from framework.arguments import Arguments

import testsconf


# ----------------------------------------------------------------------
#    EXAMPLE TEST RUNNER
# ----------------------------------------------------------------------
class ExampleRunner(TestRunner):

    def __init__(self, arguments, output_dir, supported_tests, tests_dir):
        super().__init__(arguments, output_dir, supported_tests, tests_dir)


# ----------------------------------------------------------------------
#    ADDING CUSTOM ARGUMENTS
# ----------------------------------------------------------------------
def _add_custom_arguments(self):
    # For echo/custom_arg test
    self._parser.add_argument(
            '--custom',
            type=str,
            default="default custom string",
            help='Custom string argument.'
    )
    # For spirent/*tests
    self._parser.add_argument(
        '-s', '--server',
        type=str,
        default='terminal.liberouter.org',
        help='Spirent TestCenter server address'
    )
    self._parser.add_argument(
        '-c', '--chassis',
        type=str,
        default='spirent.liberouter.org',
        help='Spirent TestCenter chassis address'
    )
    self._parser.add_argument(
        '-p', '--port',
        type=str,
        default=None,
        help='Spirent TestCenter chassis port'
    )
    self._parser.add_argument(
        '--dcpro-mode',
        action='store_true',
        default=False,
        help='Run tests in "DCPro" mode (FEC control, ...).'
    )

Arguments._add_arguments = _add_custom_arguments


# ----------------------------------------------------------------------
#     MAIN
# ----------------------------------------------------------------------

def main():

    args = Arguments().parse()

    tests_dir = testsconf.tests_dir
    if not os.path.isabs(tests_dir):
        this_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
        tests_dir = os.path.abspath(os.path.join(this_dir, tests_dir))

    output_dir = args.odir
    if not os.path.isabs(output_dir):
        this_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
        output_dir = os.path.abspath(os.path.join(this_dir, output_dir))

    tests_runner = ExampleRunner(args, output_dir, testsconf.tests, tests_dir)

    if tests_runner.run():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
