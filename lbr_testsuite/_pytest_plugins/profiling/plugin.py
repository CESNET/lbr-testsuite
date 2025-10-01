"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Pytest plugin with profiler fixtures.
"""

import functools

from pytest_cases import fixture

from ...common.common import compose_output_path
from ...profiling import MultiProfiler, ProcessEngine, application


def pytest_addoption(parser):
    application.add_cli_arguments(parser.addoption)


@fixture(scope="function")
def profilers_output_dir():
    """Define a directory where all profilers output will be placed.

    Redefine this fixture to change the directory. By default, outputs
    are stored in the current working directory.

    Returns
    -------
    str
        Path to a directory for profilers output.
    """

    return ""


@fixture(scope="function")
def concurrent_profiler_engine():
    """This fixture defines which concurrent engine will be used for
    profilers provided by `profiler` fixture.

    Returns
    -------
    type[ConcurrentEngine]
        Class implementing concurrent engine.
    """

    return ProcessEngine


@fixture(scope="function")
def profiler(request, profilers_output_dir, concurrent_profiler_engine):
    prof = MultiProfiler(
        application.collect_profilers(
            get_option_cbk=request.config.getoption,
            path_compose_cbk=functools.partial(compose_output_path, request),
            profilers_output_dir=profilers_output_dir,
            concurrent_engine=concurrent_profiler_engine,
        )
    )

    yield prof

    prof.stop()
    prof.join()
