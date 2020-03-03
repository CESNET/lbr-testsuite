"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala, Ivan Hazucha)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Argument parser class for testing suite.

    Contains common arguments definition and method for parsing command line arguments
    with a basic sanity check.
"""

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


class Arguments:

    DESCRIPTION = (
        "This is a testing suite for creation of various automatic tests."
    )
    EXAMPLE = (
        "Example usage: python36 <program> -o \"<outputfile>\" -i \"<included/tests>\" -e \"<excluded/tests>\*"
    )


    def __init__(self):
        self._args = None
        self._parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter,
            description=Arguments.DESCRIPTION,
            epilog=Arguments.EXAMPLE
        )


    def parse(self, args=None):
        """
        Parse arguments.
        """
        self._add_common_arguments()
        self._add_arguments()

        self._args = self._parser.parse_args(args)

        if not self._args.include:
            # Handle default value for "include" list (as standard argparse default cannot be used
            # due to action = 'append').
            self._args.include = ['*']
        elif any(isinstance(it, list) for it in self._args.include):
            # Flatten the include list if "include" arg has been used more than once.
            _aux = self._args.include.copy()
            self._args.include = [it for sublist in _aux for it in sublist]

        if any(isinstance(it, list) for it in self._args.exclude):
            # Flatten the exclude list if "exclude" arg has been used more than once.
            _aux = self._args.exclude.copy()
            self._args.exclude = [it for sublist in _aux for it in sublist]

        return self._args


    def _add_common_arguments(self):
        self._parser.add_argument(
                '-i', '--include',
                type=str,
                default=[],
                nargs='*',
                action='append',
                help='Tests to include'
        )
        self._parser.add_argument(
                '-e', '--exclude',
                type=str,
                default=[],
                nargs='*',
                action='append',
                help='Tests to exclude'
        )
        self._parser.add_argument(
                '-o', '--odir',
                type=str,
                default="output",
                help='Testing outputs directory'
        )
        self._parser.add_argument(
                '-M', '--manual-debug',
                action='store_true',
                default=False,
                help='Manual debugging'
        )


    def _add_arguments(self):
        """
        Method to be overridden if needed (i.e. if custom arguments needs to be added).
        """
        # self._parser.add_argument(...)
        ...


    @property
    def args(self):
        return self._args
