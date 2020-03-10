"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala, Ivan Hazucha)
Copytight: (C) 202O CESNET
License: GPL-2.0

Argument parser module.

Contains common arguments definition, method for parsing command line arguments
and basic sanity check.
"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


class Arguments:
    """Arguments class for command line arguments processing.

    Attributes
    ----------
    args : ArgumentParser.parseargs() populated namespace
        Set of parsed arguments.
    _parser : ArgumentParser
        Argument parser object.

    Methods
    -------
    parse(args=None)
        Parse arguments and set default argument values.
    add_arguments
        Method for custom arguments definition.
    """

    _DESCRIPTION = (
        "This is a testing suite for creation of various automatic tests."
    )

    _EXAMPLE = (
        "Example usage: python3.6 <test-runner> -o \"<outputfile>\" -i \"<included/tests>\" -e \"<excluded/tests>\*"
    )


    def __init__(self):
        self.args = None
        self._parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter,
            description=Arguments._DESCRIPTION,
            epilog=Arguments._EXAMPLE
        )


    def parse(self, args=None):
        """Parse arguments and set defaults.

        Parameters:
        -----------
        args: str, optional
            List of strings to parse. The default is taken from sys.argv

        Returns:
        --------
        ArgumentParser.parseargs() populated namespace
            Set of arguments with their default values or values parsed from args parameter.
        """

        self._add_common_arguments()
        self.add_arguments()

        self.args = self._parser.parse_args(args)

        if not self.args.include:
            # Handle default value for "include" list (as standard argparse default cannot be used
            # due to action = 'append').
            self.args.include = ['*']
        elif any(isinstance(it, list) for it in self.args.include):
            # Flatten the include list if "include" arg has been used more than once.
            _aux = self.args.include.copy()
            self.args.include = [it for sublist in _aux for it in sublist]

        if any(isinstance(it, list) for it in self.args.exclude):
            # Flatten the exclude list if "exclude" arg has been used more than once.
            _aux = self.args.exclude.copy()
            self.args.exclude = [it for sublist in _aux for it in sublist]

        return self.args


    def _add_common_arguments(self):
        """Add common arguments.

        These arguments are common for all tests and servers for general setup.
        """

        self._parser.add_argument(
                '-i', '--include',
                type=str,
                default=[],
                nargs='*',
                action='append',
                help='Tests to include. Supports *-globbing, can be used multiple times.'
        )
        self._parser.add_argument(
                '-e', '--exclude',
                type=str,
                default=[],
                nargs='*',
                action='append',
                help='Tests to exclude. Supports *-globbing, can be used multiple times.'
        )
        self._parser.add_argument(
                '-o', '--odir',
                type=str,
                default="output",
                help='Testing outputs directory.'
        )
        self._parser.add_argument(
                '-M', '--manual-debug',
                action='store_true',
                default=False,
                help='Manual debugging mode (implementation is test-specific).'
        )


    def add_arguments(self):
        """Method for definition of custom arguments.

        This method is intended to be overridden if needed (i.e. if custom arguments
        needs to be added). This should be done in a script responsible for arguments
        handling (mostly the script running tests).
        """
        # self._parser.add_argument(...)

        ...
