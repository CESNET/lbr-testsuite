"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Testing of executable module features. As common features of
executable.executable is tested in test_tool.py, these tests focuses
mainly on executable.executable.Daemon features.
"""

import logging
import pathlib
import subprocess
import time

import pytest

from lbr_testsuite.executable import coredump, executable, strace
from lbr_testsuite.executable.local_executor import LocalExecutor
from lbr_testsuite.executable.remote_executor import RemoteExecutor

from .conftest import match_syscalls


TESTING_OUTPUT = "I am testing myself!"

TIME_MEASUREMENT_TOLERANCE = 0.2


def test_daemon_simple_args(helper_app, testing_namespace, executor):
    """Test successful execution of a simple command with arguments.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        [helper_app, "-f", "5", "-o", TESTING_OUTPUT, "-e", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT + TESTING_OUTPUT
    assert stderr == ""


def test_daemon_simple_args_str(helper_app, testing_namespace, executor):
    """Test successful execution of a simple command with arguments.

    Passing command as a string.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        f'{helper_app} -f 5 -o "{TESTING_OUTPUT}" -e "{TESTING_OUTPUT}"',
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT + TESTING_OUTPUT
    assert stderr == ""


def test_daemon_finished(helper_app, testing_namespace, executor):
    """Test successful execution of a simple command with arguments
    which ends before it is stopped.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        [helper_app, "-o", TESTING_OUTPUT, "-e", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert not cmd.is_running()
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT + TESTING_OUTPUT
    assert stderr == ""


def test_daemon_simple_args_allowed_failure(helper_app, testing_namespace, executor):
    """Test of command which is allowed to fail.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        [helper_app, "-r", "2", "-e", TESTING_OUTPUT],
        failure_verbosity="no-exception",
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_daemon_simple_args_expected_failure(helper_app, testing_namespace, executor):
    """Test of command which is expected to fail.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        [helper_app, "-r", "2"],
        failure_verbosity="no-error",
        netns=testing_namespace,
        executor=executor,
    )

    with pytest.raises(executable.ExecutableProcessError):
        cmd.start()
        time.sleep(1)  # wait some time so helper_app can register signal handlers
        cmd.stop()


def test_daemon_is_running(helper_app, testing_namespace, executor):
    """Test that running command check is working - running command.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    outputs_interval = 3
    outputs_multiplier = 2
    test_duration = outputs_multiplier * outputs_interval + 2
    cmd = executable.Daemon(
        [helper_app, "-f", str(outputs_interval), "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(test_duration)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    stdout, stderr = cmd.stop()
    assert not cmd.is_running()

    # TESTING_OUTPUT is printed right away and every outputs_interval second
    assert stdout == TESTING_OUTPUT * (1 + outputs_multiplier)
    assert stderr == ""


def test_daemon_is_running_wait(helper_app, testing_namespace, executor):
    """Test that the 'is_running()' method correctly waits the specified amount
    of time before checking command status. The command should be active.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    outputs_interval = 3
    outputs_multiplier = 2
    test_duration = outputs_multiplier * outputs_interval + 2
    cmd = executable.Daemon(
        [helper_app, "-f", str(outputs_interval), "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    t_start = time.time()
    assert cmd.is_running(after=test_duration)
    t_diff = time.time() - t_start
    assert t_diff > test_duration and t_diff < test_duration + TIME_MEASUREMENT_TOLERANCE
    stdout, stderr = cmd.stop()
    assert not cmd.is_running()

    # TESTING_OUTPUT is printed right away and every outputs_interval second
    assert stdout == TESTING_OUTPUT * (1 + outputs_multiplier)
    assert stderr == ""


def test_daemon_not_running(helper_app, testing_namespace, executor):
    """Test that running command check is working - exited command.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon(
        [helper_app, "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert not cmd.is_running()
    stdout, stderr = cmd.stop()
    assert not cmd.is_running()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_daemon_returncode_finished(helper_app, testing_namespace, executor):
    """Test return code of successful execution of a simple command
    which ends before it is stopped.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon([helper_app], netns=testing_namespace, executor=executor)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert not cmd.is_running()

    assert cmd.returncode() == 0


def test_daemon_returncode_stopped(helper_app, testing_namespace, executor):
    """Test return code of successful execution of a simple command
    terminated by stop() method.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon([helper_app, "-f", "5"], netns=testing_namespace, executor=executor)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    cmd.stop()

    assert cmd.returncode() == 0


def test_daemon_returncode_none(helper_app, testing_namespace, executor):
    """Test return code of all stages of successful execution of
    a simple command terminated by stop() method.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Daemon([helper_app, "-f", "5"], netns=testing_namespace, executor=executor)

    assert cmd.returncode() is None

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    assert cmd.returncode() is None

    cmd.stop()

    assert cmd.returncode() == 0


def test_daemon_returncode_expected_failure(helper_app, testing_namespace, executor):
    """Test return code of failed command."""

    exp_retcode = 2

    cmd = executable.Daemon(
        [helper_app, "-f", "5", "-r", str(exp_retcode)],
        failure_verbosity="no-error",
        netns=testing_namespace,
        executor=executor,
    )

    with pytest.raises(executable.ExecutableProcessError):
        cmd.start()
        time.sleep(1)  # wait some time so helper_app can register signal handlers
        cmd.stop()

    assert cmd.returncode() == exp_retcode


def test_daemon_outputs_mixed(tmp_files, helper_app, testing_namespace):
    """Test of outputs setting - stdout and stderr are mixed to a single
    file.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon(
        f'{helper_app} -f 5 -o "{TESTING_OUTPUT}" -e "{TESTING_OUTPUT}"',
        netns=testing_namespace,
    )
    cmd.set_outputs(str(tmp_files["stdout"]))

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout is None and stderr is None
    assert tmp_files["stdout"].exists()
    with open(tmp_files["stdout"], "r") as of:
        assert of.read() == f"{TESTING_OUTPUT}{TESTING_OUTPUT}"


def test_daemon_outputs_separated(tmp_files, helper_app, testing_namespace):
    """Test of outputs setting - stdout and stderr are separated to
    different files.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    err_testing_output = f"err: {TESTING_OUTPUT}"
    cmd = executable.Daemon(
        f'{helper_app} -f 5 -o "{TESTING_OUTPUT}" -e "{err_testing_output}"',
        netns=testing_namespace,
    )
    cmd.set_outputs(stdout=str(tmp_files["stdout"]), stderr=str(tmp_files["stderr"]))

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout is None and stderr is None
    assert tmp_files["stdout"].exists()
    assert tmp_files["stderr"].exists()
    with open(tmp_files["stdout"], "r") as of:
        assert of.read() == TESTING_OUTPUT
    with open(tmp_files["stderr"], "r") as of:
        assert of.read() == err_testing_output


def test_daemon_coredump(require_root, tmp_files, helper_app, testing_namespace, executor):
    """Test that a failed command produces a coredump.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    if isinstance(executor, RemoteExecutor):
        pytest.skip(f"remote executor does not support coredump")

    cd = coredump.Coredump()
    cd.set_output_file(tmp_files["core"])
    cmd = executable.Daemon(
        [helper_app, "-f", "2", "-s"],
        default_logger_level=logging.CRITICAL + 1,
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_coredump(cd)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can start and fail
    assert not cmd.is_running()
    with pytest.raises(executable.ExecutableProcessError, match="died with <Signals.SIGSEGV"):
        cmd.stop()

    assert pathlib.Path(cd.get_output_file()).exists()


def test_daemon_strace(tmp_files, helper_app, testing_namespace, executor):
    """Test that a commad produces a strace.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    if isinstance(executor, RemoteExecutor):
        pytest.skip(f"remote executor does not support strace")

    st = strace.Strace()
    st.set_output_file(tmp_files["strace"])
    cmd = executable.Daemon([helper_app, "-f", "2"], netns=testing_namespace, executor=executor)
    cmd.set_strace(st)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    cmd.stop()

    assert pathlib.Path(st.get_output_file()).exists()


def test_daemon_strace_expressions_coredump(
    require_root, tmp_files, helper_app, testing_namespace, executor
):
    """Test that a commad produces a strace with specified system calls
    only together with a coredump.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    if isinstance(executor, RemoteExecutor):
        pytest.skip(f"remote executor does not support strace/coredump")

    strace_expressions = ("open", "read")
    st = strace.Strace()
    st.set_output_file(tmp_files["strace"])
    st.add_expression(strace_expressions)
    cd = coredump.Coredump()
    cd.set_output_file(tmp_files["core"])
    cmd = executable.Daemon(
        [helper_app, "-f", "2", "-s"],
        default_logger_level=logging.CRITICAL + 1,
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_strace(st)
    cmd.set_coredump(cd)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can start and fail
    assert not cmd.is_running()
    with pytest.raises(executable.ExecutableProcessError, match="died with <Signals.SIGSEGV"):
        cmd.stop()

    assert pathlib.Path(st.get_output_file()).exists()
    assert pathlib.Path(cd.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions, segfault=True)


def test_daemon_sigterm_error(executor):
    """Test that a command with return code -signal.SIGTERM produces
    an error.
    """

    if isinstance(executor, RemoteExecutor):
        pytest.skip(
            f"remote executor does not report correct return code when process is killed by signal"
        )

    cmd = executable.Daemon(["ping", "127.0.0.1"], failure_verbosity="no-error", executor=executor)
    cmd.start()

    with pytest.raises(executable.ExecutableProcessError):
        cmd.stop()


def test_daemon_sigterm_ok(executor):
    """Test that a command with return code -signal.SIGTERM is allowed
    (i.e. does not fail).
    """

    if isinstance(executor, RemoteExecutor):
        pytest.skip(
            f"remote executor does not report correct return code when process is killed by signal"
        )

    cmd = executable.Daemon(
        ["ping", "127.0.0.1"],
        failure_verbosity="no-error",
        sigterm_ok=True,
        executor=executor,
    )
    cmd.start()

    cmd.stop()
