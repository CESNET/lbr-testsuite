"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2021 CESNET

Renamer pytest plug-in. It enables to rename each test execution
specifically, e.g., it prefixes all tests by a string specified
on command line.
"""

import pytest


def pytest_addoption(parser):
    """Standard pytest hook to handle command line. It defines
    `renamer_prefix` command line option.

    Parameters
    ----------
    parser : _pytest.config.argparsing.Parser
        Pytest parser object
    """

    parser.addoption(
        "--renamer-prefix",
        default=None,
        help=("Prefix each test by a specified string."),
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """Special pytest hook which enables us to further modify each
    test execution. Here, we rename all tests according the command
    line arguments.
    """

    prefix = config.getoption("renamer_prefix")

    if not prefix or len(prefix) == 0:
        return

    for item in items:
        item._nodeid = prefix + "/" + item._nodeid
