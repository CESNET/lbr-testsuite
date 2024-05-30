"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2022 CESNET

Registration of implemented topologies.
"""

_REGISTERED_OPTIONS = dict()


def topology_option_register(option_name):
    """Register a topology option in topology module.

    Registration ensures creation of a fixture named
    'option_``option_name``'. Such fixture is needed in a topology
    definition to access topology argument value.

    Parameters
    ----------
    option_name: str
        Name of topology option.
    """

    global _REGISTERED_OPTIONS
    assert option_name not in _REGISTERED_OPTIONS, "Topology option already registered."

    pseudofixture_name = f"option_{option_name}"
    _REGISTERED_OPTIONS[option_name] = dict(
        option_name=option_name,
        pseudofixture=pseudofixture_name,
    )


def registered_topology_options():
    """Get global dictionary of registered topology options.

    Return
    ------
    dict
        Dictionary of registered topology options.
    """

    global _REGISTERED_OPTIONS
    return _REGISTERED_OPTIONS
