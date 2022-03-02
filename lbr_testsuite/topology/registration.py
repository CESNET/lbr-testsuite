"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2022 CESNET

Registration of implemented topologies.
"""


_REGISTERED_TOPOLOGIES = dict()


def topology_register(name, option_name):
    """Register a topology implementation in topology module.

    Registration ensures creation of a fixture named
    'option_``option_name``'. Such fixture is needed in a topology
    definition to access topology argument value.

    Parameters
    ----------
    name: str
        Unique topology identification.
    option_name: str
        Name of topology option.
    """

    global _REGISTERED_TOPOLOGIES
    assert name not in _REGISTERED_TOPOLOGIES, 'Topology already implemented.'

    pseudofixture_name = f'option_{option_name}'
    _REGISTERED_TOPOLOGIES[name] = dict(
        option_name=option_name,
        pseudofixture=pseudofixture_name
    )


def registered_topologies():
    """Get global dictionary of registered topologies.

    Return
    ------
    dict
        Dictionary of registered topologies.
    """

    global _REGISTERED_TOPOLOGIES
    return _REGISTERED_TOPOLOGIES
