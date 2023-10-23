"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2023 CESNET, z.s.p.o.

VLAN configuration plugin.
"""

from pytest_cases import fixture

from ...vlan_config.vlanconfig import VLANConfig


def pytest_addoption(parser):
    parser.addoption(
        "--access-vlan",
        type=int,
        default=None,
        help=(
            "ID of access VLAN. Access VLAN is used when a non-VLAN traffic "
            "has to be generated and sent via switch. Use access VLAN configured "
            "on switch for target server. If a VLAN traffic is to be generated "
            "use --trunk-vlans instead."
        ),
    )
    parser.addoption(
        "--trunk-vlans",
        type=str,
        default=None,
        help=(
            "IDs of trunk VLANs. Argument is a comma separated "
            "list of VLAN IDs. Trunk VLANs are used when a VLAN traffic has to "
            "be sent via switch (loopback over switch, VLAN traffic "
            "generator, ...). Trunk VLAN(s) configured on switch for given "
            "server has to be used as access VLAN ID is stripped and traffic "
            "from other VLANs are dropped."
        ),
    )


@fixture
def vlans_config(request):
    """Fixture for initialization and usage of VLAN configuration class.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture, here used for accessing of CLI
        arguments.

    Returns
    -------
    VLANConfig
        Initialized instance of VLANConfig class.
    """

    access_vlan = request.config.getoption("access_vlan")
    try:
        trunk_vlans_str = request.config.getoption("trunk_vlans").split(",")
        trunk_vlans = list(map(int, trunk_vlans_str))
    except AttributeError:
        trunk_vlans = None

    return VLANConfig(access_vlan, trunk_vlans)
