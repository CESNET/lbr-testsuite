"""Package containing framework for automated tests creation.

Automated tests, created using this framework, are created by implementing various tests
as a subclasses of BasteTest class and by implementing a test-runnerm using TestRunner
class for tests execution.

The package consits of the following modules:
---------------------------------------------
Arguments - is responsible for handling command line arguments.
Logger - provides a facility for logging information about tests execution.
Results generator - a module for generation of results HTML page.
Base test - a test class prescription used as a frame for all implemented tests. Particular
    tests should be implemented as a sublclass of this class via extension of its methods.
Test case data - a simple class holding a setup of particular test case (as a test typically
    consists of multiple test cases).
Test result - a simple class for storage of results from all executed tests. Based on these
    results a final summary report is generated.
Test runner - a class for execution of all requested tests.
"""

from .arguments        import Arguments
from .basetest         import BaseTest
from .logger           import Logger
from .resultgenerator  import generate_html
from .testcasedata     import TestCaseData
from .testresult       import TestResult
from .testrunner       import TestRunner