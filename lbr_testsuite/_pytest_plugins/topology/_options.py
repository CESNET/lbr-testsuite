"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2022 CESNET

Command line options registration for topologies.
"""

"""
List of registered topology options. Options are defined as pairs where
first item is a list of option names, second is a dictionary of
arguments defined by _pytest.config.argparsing.Parser.addoption() method.
"""
_OPTIONS = list()


def add_option(option):
    """Add a topology option

    Parameters
    ----------
    option: tuple(list(), dict())
        option: tuple(list(), dict())
        Pair defining an option (see ``_OPTIONS`` description for more
        details).
    """

    global _OPTIONS
    _OPTIONS.append(option)


def options():
    """Get list of topology options

    Returns
    -------
    list(dict())
        List of topology options.
    """

    global _OPTIONS
    return _OPTIONS
