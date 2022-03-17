"""
Author(s): Pavel Krobot <pavel.krobot@cesnet.cz>,
    Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Topology plugin implementation.
"""

import pytest
import pytest_cases
from pathlib import Path

from ...executable import executable
from ...topology.device import PciDevice
from ...topology.topology import Topology, select_topologies
from ...topology import registration

from . import _options
from ._wired_loopback import topology_wired_loopback  # noqa
from ._virtual_devices import topology_vdev_loopback, topology_vdev_ring  # noqa
from ._spirent import topology_wired_spirent  # noqa


def pytest_addoption(parser):
    for args, kwargs in _options.options():
        parser.addoption(*args, **kwargs)


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
    metafunc.parametrize(pseudofixture, options, scope='session')


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
        if not hasattr(item, 'callspec'):
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
            topology['pseudofixture'],
            config.getoption(topology['option_name'])
        )


def pytest_collection_modifyitems(session, config, items):
    """Special pytest hook which enables us to further modify each
    parametrization of the test function call created using the previous
    pytest_generate_tests hook. We filter and mark as deselected the
    runs that uses undefined pseudofixtures.
    """

    pseudofixtures = [t['pseudofixture'] for t in registration.registered_topology_options().values()]
    filtered = []

    # Deselect all the test runs having any pseudofixture not defined
    _filter_undefined_pseudofixtures(items, filtered, pseudofixtures)
    config.hook.pytest_deselected(items=filtered)


# Select the default topology for all the tests
# if it is not directly overridden by the test module.
select_topologies(['topology_wired_loopback'])


@pytest_cases.fixture(scope='module')
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


@pytest_cases.fixture(scope='module')
def device_bound(request, require_root, device):
    """Fixture which bounds the driver of the PCI device, for other type
    of devices it has no effect.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture
    require_root : Fixture
        Fixture checking we are running under the root
    device : Device
        An instance of Device to be bound

    Returns
    -------
    Device
        bound device object
    """

    if isinstance(device, PciDevice):
        root_dir = Path(request.config.getoption('repository_root')).resolve()
        utility = root_dir / request.config.getoption('dcpro_autobind_exec')
        executable.Tool([str(utility), '-d', str(device.get_address())]).run()

    return device
