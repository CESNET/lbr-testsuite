"""
Author(s):
    Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Spirent class fixtures.
"""

from pytest_cases import fixture

from lbr_testsuite import spirent as lbrt_spirent


DEFAULT_CONFIG_FILENAME_BASE = "default_config"


def pytest_addoption(parser):
    parser.addoption(
        "--spirent-config-mapping",
        action="append",
        default=[],
        type=str,
        help=(
            "Add a port mapping to default configuration filename suffix "
            "in a form <port-number>,<suffix>. Based on spirent port, "
            "spirent configuration file is determined by composition of "
            "default configuration filename base, this suffix and '.xml'"
            "file extension. Example: \n"
            "We selected spirent port 7/1 with mapping: "
            "'--spirent-config-mapping=7/1,original'. Configuration file"
            "'default_config_original.xml' will be used as a default"
            "spirent configuration file."
        ),
    )


@fixture(scope="module")
def spirent_config_suffix(request, generator):
    """Fixture providing spirent configuration file suffix based on
    per-port mapping.

    Parameters
    ----------
    request: Fixture
        Special pytest fixture (here for acquiring command line
        arguments).
    generator : Spirent
        An initialized instance of Spirent generator.

    Returns
    -------
    str
        Configuration file suffix.
    """

    assert isinstance(generator, lbrt_spirent.Spirent)

    port_cfg_mappings = request.config.getoption("spirent_config_mapping")
    port_cfg_mappings = [mapping.split(",") for mapping in port_cfg_mappings]
    port_cfg_mappings = {port: suffix for port, suffix in port_cfg_mappings}

    spirent_port = generator.get_port()
    cfg_suffix = ""
    if port_cfg_mappings.get(spirent_port) is not None:
        cfg_suffix = f"_{port_cfg_mappings[spirent_port]}"

    return cfg_suffix


@fixture(scope="module")
def spirent(request, generator, spirent_config_suffix):
    """Fixture representing spirent.

    Parameters
    ----------
    generator : Spirent
        An initialized instance of Spirent generator.
    spirent_config_suffix : str (fixture)
        Spirent configuration file suffix for used spirent port.

    Returns
    -------
    Spirent
        Returns initialized instance of Spirent generator with
        spirent connected.
    """

    assert isinstance(generator, lbrt_spirent.Spirent)

    cfg_file_name = f"{DEFAULT_CONFIG_FILENAME_BASE}{spirent_config_suffix}.xml"
    cfg_dir = request.node.path.parent.resolve()
    default_configuration_file = str(cfg_dir / cfg_file_name)
    generator.set_config_file(default_configuration_file)

    return generator


@fixture(scope="module")
def spirent_configured(spirent):
    """Fixture for hadling configuration and corresponding cleanup
    of connected spirent.

    If `spirent` fixture is not reimplemented, default configuration
    is used. To use custom configuration file, define spirent fixture
    inside your test using following template:

    .. code-block:: python

        @fixture
        def spirent(spirent):
            spirent.set_config_file(<PATH_TO_THE_CONFIG>)
            return spirent

    Parameters
    ----------
    spirent : Spirent
        An instance of initialized and connected Spirent
        generator.
    """

    spirent.load_config_and_connect_chassis_port()
    yield spirent

    spirent.disconnect_chassis()
