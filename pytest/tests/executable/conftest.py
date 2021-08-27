"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Common sources for executable module testing.
"""

import pathlib
import subprocess

import pytest_cases


def _this_test_dir():
    return pathlib.Path(__file__).parent.resolve()


@pytest_cases.fixture(scope='session')
def helper_app(tmp_path_factory):
    """Path to testing helper application.

    Parameters
    ----------
    tmp_path_factory : pytest.TempPathFactory
        Session-scoped fixture for acquiring of tests temporary
        directory.

    Returns
    -------
    str
        Path to the application.
    """

    app_source = str(_this_test_dir() / 'helper' / 'helper_app.c')
    app = str(tmp_path_factory.getbasetemp() / 'helper_app')
    subprocess.run(['gcc', app_source, '-o', app], check=True)

    return app


@pytest_cases.fixture
def tmp_files(request, tmp_path):
    """Temporary output files for executable module tests.

    Parameters
    ----------
    request : pytest.FixtureRequest
        Special pytest fixture. Here used for accessing a test name.
    tmp_path : pathlib.Path (fixture)
        pytest fixture providing a path to a temporary location.

    Returns
    -------
    dict(str)
        Paths to temporary output files for:
        - stdout,
        - stderr,
        - coredump,
        - strace.
    """

    tmp_file_base = tmp_path / request.node.name
    tmp_files = dict()
    for ft in ('stdout', 'stderr', 'core', 'strace'):
        tmp_files[ft] = pathlib.Path(f'{tmp_file_base}.{ft}')
    return tmp_files


def match_syscalls(file_path, expressions, segfault=False):
    """Match lines of a file with expressions.

    Each line except last N (N changes based on segfault flag) should
    contain a syscall from expressions.

    Parameters
    ----------
    file_path : str
        Path to a strace file.
    expressions : list(str)
        List of syscalls expressions.
    segfault : bool (optional)
        Flag whether a related command died on a segfault.

    Returns
    -------
    bool
        True when all syscall lines contains a syscall from expected
        expressions. False otherwise.
    """

    non_expr_lines = 5 + len(expressions)
    if segfault:
        non_expr_lines += 1
    with open(file_path, 'r') as f:
        for line in f.readlines()[:-non_expr_lines]:
            sys_call = line.split()[3]
            if not list(filter(sys_call.startswith, expressions)):
                return False
    return True
