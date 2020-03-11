"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>
Copytight: (C) 202O CESNET
License: GPL-2.0

Test case data module contains simple class, used within all tests as a test case setup.

Contains common test case data properties and a method for test specific properties definition.
"""


class TestCaseData:
    """Test case data class containing test case setup.

    Attributes
    ----------
    case_name : str
        A test case name.

    Methods
    -------
    init_test_specific_properties()
        Method inteded to be defined within the implementation of a test. Custom test specific
        properties is added to TestCaseData object via this function.
    """


    def __init__(self):
        self.case_name = None
        # Other common TestCaseData properties ..

        self.init_test_specific_properties()


    def init_test_specific_properties(self):
        """Init method for custom test specific properties.

         Overriding of this method within a test implementation is expected.
         """

        ...