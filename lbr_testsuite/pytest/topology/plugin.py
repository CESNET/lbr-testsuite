"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2021 CESNET

Topology fixtures.
"""

import pytest
import pytest_cases
from pathlib import Path

from ...executable import executable
from ...common.sysctl import sysctl_set, sysctl_set_with_restore
from ...ipconfigurer import ipconfigurer as ipconf
from ...topology.device import PciDevice, RingDevice, PcapLiveDevice
from ...topology.generator import NetdevGenerator
from ...topology.topology import Topology, select_topologies
from ...topology.pci_address import PciAddress
from ...topology import registration


def pytest_addoption(parser):
    parser.addoption(
        '--wired-loopback',
        action='append',
        default=[],
        type=str,
        help=(
            'Add wired loopback topology of two ports, the first is a kernel interface '
            '(its name or its PCI address) the second is PCI address. (Example: '
            'tge3,0000:01:00.0 or 0000:04:00.0,0000:04:00.1).'
        )
    )

    parser.addoption(
        '--vdevs',
        action='store_true',
        default=None,
        help=(
            'Enable virtual topologies, e.g., vdev_loopback and vdev_ring. This collects '
            'also tests that supports these virtual topologies. By default virtual '
            'topologies are disabled.'
        )
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
    for topology in registration.registered_topologies().values():
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

    pseudofixtures = [t['pseudofixture'] for t in registration.registered_topologies().values()]
    filtered = []

    # Deselect all the test runs having any pseudofixture not defined
    _filter_undefined_pseudofixtures(items, filtered, pseudofixtures)
    config.hook.pytest_deselected(items=filtered)


@pytest_cases.fixture(scope='session')
def topology_wired_loopback(request, option_wired_loopback):
    """Fixture creating wired loopback topology. Unlike vdev_loopback,
    it is uses real NIC interfaces to build Device and Generator objects
    on top of a real NIC.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture

    Returns
    -------
    Topology
        An instance of Topology representing wired loopback
    """

    # Workaroud for a weird bug in pytest_cases similar to
    # https://github.com/smarie/python-pytest-cases/issues/37
    if (option_wired_loopback == pytest_cases.NOT_USED):
        return  # skip the fixture if its parameter not used

    wlpbk = option_wired_loopback.split(",")
    if len(wlpbk) < 2:
        pytest.skip("wired loopback is missing PCI address (see --wired-loopback)")

    if PciAddress.is_valid(wlpbk[0]):
        root_dir = Path(request.config.getoption('repository_root')).resolve()
        utility = root_dir / request.config.getoption('dcpro_autobind_exec')
        executable.Tool([str(utility), '-d', wlpbk[0], '-m', 'kernel']).run()

    device = PciDevice(wlpbk[1])
    generator = NetdevGenerator(wlpbk[0])

    sysctl_set_with_restore(request, f'net.ipv6.conf.{generator.get_netdev()}.disable_ipv6', '1')

    return Topology(device, generator)


registration.topology_register('wired-loopback', 'wired_loopback')


@pytest_cases.fixture(scope='session')
def topology_vdev_loopback(request, require_root, option_vdevs):
    """Fixture creating virtual loopback topology. Internally, it adds
    veth network interfaces pair (testing-vdev0p0 and testing-vdev0p1).
    The first interface is used to build the Device object, the second
    is used to build the Generator object.
    """

    vethpeers = ('testing-vdev0p0', 'testing-vdev0p1')

    ipconf.add_link(vethpeers[0], kind='veth', peer=vethpeers[1])
    request.addfinalizer(lambda: ipconf.delete_link(vethpeers[0]))

    ipconf.ifc_up(vethpeers[0])
    request.addfinalizer(lambda: ipconf.ifc_down(vethpeers[0]))

    sysctl_set(f'net.ipv6.conf.{vethpeers[0]}.disable_ipv6', '1')
    sysctl_set(f'net.ipv6.conf.{vethpeers[1]}.disable_ipv6', '1')

    device = PcapLiveDevice(vethpeers[0])
    generator = NetdevGenerator(vethpeers[1])

    return Topology(device, generator)


@pytest_cases.fixture(scope='session')
def topology_vdev_ring(option_vdevs):
    """Fixture creating virtual ring topology. Internally, the topology
    is build only on top of RingDevice object without any traffic
    generator (Generator object). Packets transmitted on the device are
    received again.
    """

    device = RingDevice()
    return Topology(device)


registration.topology_register('virtual-devices', 'vdevs')


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
