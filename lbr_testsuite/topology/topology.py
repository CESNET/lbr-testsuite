"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2022 CESNET

Topology class and topology helpers.
"""

from warnings import warn

import pytest
from pytest_cases.common_pytest import extract_parameterset_info, get_fixture_name
from pytest_cases.fixture__creation import get_caller_module
from pytest_cases.fixture_core1_unions import UnionFixtureAlternative, _fixture_union

from .analyzer import Analyzer
from .device import Device
from .generator import Generator


class Topology:
    """Topology class. A topology object represents a tuple of three
    elements - a generator object, a device object and an analyzer
    object (generator and analyzer might be aggregated into single
    object).

    Attributes
    ----------
    _device : device.Device
        Topology device.
    _generator : generator.Generator
        Topology generator.
    _analyzer : analyzer.Analyzer
        Topology analyzer.
    """

    def __init__(self, device, generator=None, analyzer=None):
        """Creates a topology from its components.

        Parameters
        ----------
        device : device.Device
            building device object
        generator : generator.Generator, optional
            building generator object
        analyzer : analyzer.Analyzer, optional
            building analyzer object

        Raises
        ------
        RuntimeError
            If device is not an instance of Device, or not set. If
            generator set and not an instance of Generator or if
            analyzer set and not an instance of Analyzer.
        """

        if not isinstance(device, Device):
            classname = type(device).__name__
            raise RuntimeError(f"expected instance of Device, but got {classname}")

        self._device = device

        if generator is not None and not isinstance(generator, Generator):
            classname = type(generator).__name__
            raise RuntimeError(f"expected instance of Generator, but got {classname}")

        self._generator = generator

        if analyzer is not None and not isinstance(analyzer, Analyzer):
            classname = type(analyzer).__name__
            raise RuntimeError(f"expected instance of Analyzer, but got {classname}")

        self._analyzer = analyzer

    def get_generator(self):
        """Get topology generator component.

        Returns
        -------
        generator.Generator
            topology generator
        """

        return self._generator

    def get_device(self):
        """Get topology device component.

        Returns
        -------
        device.Device
            topology device
        """

        return self._device

    def get_analyzer(self):
        """Get topology analyzer component.

        Returns
        -------
        analyzer.Analyzer
            topology analyzer
        """

        return self._analyzer

    def get_tuple(self):
        """Get tuple of the topology components.

        Returns
        -------
        tuple
            topology components
        """

        return (
            self._device,
            self._generator,
            self._analyzer,
        )

    @staticmethod
    def get_tuple_keys():
        """Get tuple of the topology component's keys.

        Returns
        -------
        tuple
            topology component's keys
        """

        return (
            "device",
            "generator",
            "analyzer",
        )


def topology_union(
    fixtures,
    name="topology",
    scope="module",
    **kwargs,
):
    """Our pytest-cases fixture_union wrapper for topology unions.
    Unfortunately it is necessary to duplicate a part of the original
    fixture_union code due to the fact that it is not possible to
    inject the caller_module into the original implementation.

    This function follows the concept of fixture unions introduced by
    the pytest-cases plugin and applies it for our specific use case
    using it on topologies. Fixture union (or topology union in our
    case) is a parametrized fixture that would first take all the
    possible values of fixture/topology A, then all possible values of
    fixture/topology B, etc.

    For example, we have two topologies, fixtures 'topology_A' and
    'topology_B':

    .. code-block:: python

        @fixture
        def topology_A(request, depsA):
            return 'topo A'

        @fixture(params=['x', 'y'])
        def topology_B(request, depsB):
            return f'topo B, param {request.param}'

    We create a topology union using:

    .. code-block:: python

        topology_union(['A', 'B'])

    It effectivelly creates a new fixture 'topology' which take all the
    values of 'topology_A', then all of 'topology_B'. Both fixtures can
    be parametrized, so'topology' takes all instances of fixtures
    entering the union.

    The simple test using topology union fixture 'topology'

    .. code-block:: python

        def test_topology_unions(topology):
            print(topology)

    thus produces::

        <...>::test_topology_unions[A] topo A  PASSED
        <...>::test_topology_unions[B-x] topo B, param x  PASSED
        <...>::test_topology_unions[B-y] topo B, param y  PASSED

    Let us assume that topologies A and B and its union are shared
    fixtures across multiple test files and are defined in conftest.py
    or any (local) pytest plugin. As a fixture with the same name can
    be overridden for a certain test folder level (see
    https://docs.pytest.org/en/stable/fixture.html#override-a-fixture-on-a-folder-conftest-level),
    the union topology fixture can also be overridden for a specific
    test file, using:

    .. code-block:: python

        @fixture
        def topology_D(request, depsB):
            return 'D opot'

        topology_union(['A', 'D'])

        def test_specific(topology):
            print(topology[::-1])  # reverse the string

    directly in a test submodule file, which produces::

        <...>::test_topology_unions[A] A opot  PASSED
        <...>::test_topology_unions[D] topo D  PASSED

    For more details behind the fixture unions have a look in the
    original pytes-cases documentation, for example:

    * https://smarie.github.io/python-pytest-cases/unions_theory/
    * https://smarie.github.io/python-pytest-cases/pytest_goodies/#fixture_union

    Parameters
    ----------
    fixtures : Iterable[str]
        fixtures to be united (can be specified without ``'name_'`` prefix)
    name : str, optional
        name of the output union fixture, otherwise name 'topology' is used
    scope : str, optional
        the scope of the output union fixture
    kwargs: optional
        other pytest-cases options of the underlying fixture_union call
    """

    # Grab the caller module, so we can create the union fixture inside it
    caller_module = get_caller_module()

    # Test the `fixtures` argument to avoid common mistakes
    if not isinstance(fixtures, (tuple, set, list)):
        raise TypeError("topology_union: the `fixtures` argument should be a tuple, set or list")

    # Unpack the pytest.param marks
    custom_pids, p_marks, fixtures = extract_parameterset_info((name,), fixtures)

    # Inject name prefixes if not already present
    prefix = f"{name}_"
    fixtures = (fix if fix.startswith(prefix) else prefix + fix for fix in fixtures)

    # Get all required fixture names
    f_names = [get_fixture_name(f) for f in fixtures]

    # Create all alternatives and reapply the marks on them
    f_alternatives = []
    f_names_args = []

    for _idx, (_name, _id, _mark) in enumerate(zip(f_names, custom_pids, p_marks)):
        # Create the alternative object
        alternative = UnionFixtureAlternative(
            union_name=name,
            alternative_name=_name,
            alternative_index=_idx,
        )

        # Remove duplicates in the fixture arguments
        if _name in f_names_args:
            warn(
                "Creating a fixture union %r where two alternatives are"
                "the same fixture %r." % (name, _name)
            )
        else:
            f_names_args.append(_name)

        # Reapply the marks
        if _id is not None or (_mark or ()) != ():
            alternative = pytest.param(alternative, id=_id, marks=_mark or ())

        f_alternatives.append(alternative)

    # Remove name prefixes from default ids if any specific ids set
    if kwargs.get("ids", None) is None:
        kwargs["ids"] = lambda ufix: ufix.alternative_name[len(prefix) :]  # noqa: E203

    union_fix = _fixture_union(
        caller_module,
        name,
        fix_alternatives=f_alternatives,
        unique_fix_alt_names=f_names_args,
        scope=scope,
        **kwargs,
    )

    return union_fix


select_topologies = topology_union
"""A readable alias for callers using topology_union functionality
when writing tests"""
