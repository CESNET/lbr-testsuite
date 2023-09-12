"""
Author(s): Pavel Krobot <pavel.krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Topology plugin implementation.
"""

import pytest
import pytest_cases

from ...topology import registration
from ...topology.devices_args import DevicesArgs
from ...topology.topology import Topology, select_topologies
from . import _options
from ._spirent import topology_wired_spirent  # noqa
from ._trex import topology_wired_trex, trex_generators, trex_manager  # noqa
from ._virtual_devices import topology_vdev_loopback, topology_vdev_ring  # noqa
from ._wired_loopback import topology_wired_loopback  # noqa


def pytest_addoption(parser):
    for args, kwargs in _options.options():
        parser.addoption(*args, **kwargs)

    parser.addoption(
        "--dpdk-devargs",
        action="append",
        default=[],
        type=str,
        help=(
            "Add DPDK devices arguments as comma separated pairs in form "
            "<device-name>[,<arg1>=<value1>[,<arg2>=<value2>...]], e.g., "
            "--dpdk-devargs=0000:01:00.0,mprq_en=1,rxqs_min_mprq=1."
        ),
    )

    parser.addini(
        "default_topology",
        type="linelist",
        default=[],
        help="Set default topology (or topologies).",
    )


def _define_pseudofixture(metafunc, pseudofixture, options):
    """Generate parametrized pseudo-fixture from options passed. A pseudo-
    -fixture is a fixture defined dynamically at run-time.
    """

    if pseudofixture not in metafunc.fixturenames:
        return

    if not options:
        # Mark this test run to be skipped and inject a special value,
        # e.g. None, as the option so we can easily recognize this
        # placeholder, i.e., when there are no commandline arguments
        # and we do not want to generate such a test run), it helps
        # us to identify and deselect the test run in the next pytest
        # hook pytest_collection_modifyitems().
        options = [pytest.param(None, marks=pytest.mark.skip)]
    elif not isinstance(options, (list, tuple)):
        options = [options]

    # Parametrize the test function creating its call for each of the options
    metafunc.parametrize(pseudofixture, options, scope="session")


def _filter_undefined_pseudofixtures(selected, filtered, pseudofixtures):
    """It filters test runs passed in `selected` based on pseudo-fixture names
    in `pseudofixtures`. If any of the pseudo-fixtures is not defined for this
    run, the run is excluded. The excluded runs are passed out of this function
    throught `filtered` list argument.
    """

    included = []
    excluded = []

    for item in selected:
        # Simply include the item if it does not have any call parameters
        if not hasattr(item, "callspec"):
            included.append(item)
            continue

        params = item.callspec.params
        exclude = False

        # Exclude if any pseudo-fixture parameter is not defined, that means
        # if the parameter is None or the parameter evaluates to False
        for pseudofix in pseudofixtures:
            if not params.get(pseudofix, True):
                exclude = True
                break

        if exclude:
            excluded.append(item)
            continue

        included.append(item)

    selected[:] = included
    filtered[:] = excluded


def pytest_generate_tests(metafunc):
    """Special pytest hook which is called when collecting a test
    function. It enables us to define so called pseudo-fixtures
    and fill them based on the command line arguments. A pseudo-
    -fixture is a fixture defined dynamically at run-time. It
    does not exist as a function or method decorated with
    @fixture anywhere.
    """

    config = metafunc.config
    for topology in registration.registered_topology_options().values():
        _define_pseudofixture(
            metafunc,
            topology["pseudofixture"],
            config.getoption(topology["option_name"]),
        )


def pytest_collection_modifyitems(session, config, items):
    """Special pytest hook which enables us to further modify each
    parametrization of the test function call created using the previous
    pytest_generate_tests hook. We filter and mark as deselected the
    runs that uses undefined pseudofixtures.
    """

    pseudofixs = [t["pseudofixture"] for t in registration.registered_topology_options().values()]
    filtered = []

    # Deselect all the test runs having any pseudofixture not defined
    _filter_undefined_pseudofixtures(items, filtered, pseudofixs)
    config.hook.pytest_deselected(items=filtered)


def pytest_sessionstart(session):
    """Standard pytest hook called when a session is started.
    It manages selection of the default topology for all tests
    This selection can be overridden by the test module for its
    tests.
    """

    default = session.config.getini("default_topology")

    if not default:
        # Our library default topology
        select_topologies(["wired_loopback"])
    else:
        select_topologies(default)


@pytest_cases.fixture(scope="module")
def topology_tuple(topology):
    """Fixture to access the topology object as a tuple of
    its attributes, components respectively. This fixture is
    internally used for unpacking the topology fixture to
    isolated attribute fixtures of it, e.g., generator,
    device fixtures derived from the topology (see below).

    Parameters
    ----------
    topology : Topology
        An instance of Topology

    Returns
    -------
    tuple
        tuple of topology object attributes (its components)
    """

    return topology.get_tuple()


# Unpack topology fixture to its attributes fixtures, this effectively
# creates, e.g., 'device' and 'generator' aliases for device and
# generator attributes.
pytest_cases.unpack_fixture(Topology.get_tuple_keys(), topology_tuple)


@pytest_cases.fixture(scope="session")
def devices_args(request):
    """Fixture creating devices arguments instance from command-line options.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture

    Returns
    -------
    DeviceArgs
        An instance of DeviceArgs representing devices arguments.
    """

    options = request.config.getoption("dpdk_devargs")
    return DevicesArgs(options)
