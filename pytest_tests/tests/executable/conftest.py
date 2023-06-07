"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Common sources for executable module testing.
"""

import os
import pathlib
import subprocess

import pyroute2
import pytest
import pytest_cases

from lbr_testsuite.executable.local_executor import LocalExecutor
from lbr_testsuite.executable.remote_executor import RemoteExecutor


def _this_test_dir():
    return pathlib.Path(__file__).parent.resolve()


@pytest_cases.fixture(scope="session")
@pytest_cases.parametrize("executor", ["local", "remote"], idgen=pytest_cases.AUTO)
def executor(request, executor):
    """Return executor.

    Parameters
    ----------
    executor : str
        Type of executor to use.
        It is either 'local' or 'remote' executor.

    Returns
    -------
    LocalExecutor or RemoteExecutor
        Executor.
    """

    if executor == "local":
        yield LocalExecutor()
    elif executor == "remote":
        remote_host = request.config.getoption("remote_host")

        if remote_host is None:
            pytest.skip(f"remote host not specified")

        remote_executor = RemoteExecutor(remote_host)
        yield remote_executor
        remote_executor.close()


@pytest_cases.fixture(scope="session")
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

    app_source = str(_this_test_dir() / "helper" / "helper_app.c")
    app = str(tmp_path_factory.getbasetemp() / "helper_app")
    subprocess.run(["gcc", app_source, "-o", app], check=True)

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
    for ft in ("stdout", "stderr", "core", "strace"):
        tmp_files[ft] = pathlib.Path(f"{tmp_file_base}.{ft}")
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
    with open(file_path, "r") as f:
        for line in f.readlines()[:-non_expr_lines]:
            sys_call = line.split()[3]
            if not list(filter(sys_call.startswith, expressions)):
                return False
    return True


@pytest_cases.fixture
@pytest_cases.parametrize("netns", [None, "lbr_testsuite_ns"], idgen=pytest_cases.AUTO)
def testing_namespace(netns):
    if netns:
        if os.geteuid() != 0:
            pytest.skip(f"namespaces are usable only under the root")

        pyroute2.netns.create(netns)
        yield netns
        pyroute2.netns.remove(netns)
    else:
        yield None


@pytest_cases.fixture(scope="session")
def require_nonroot():
    """Fixture checking whether a test is not running under the root."""

    euid = os.geteuid()

    if euid == 0:
        pytest.skip(f"test must run under non-root")
