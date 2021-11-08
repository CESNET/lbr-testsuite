"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Testing of executable module features. As common features of
executable.executable is tested in test_tool.py, these tests focuses
mainly on executable.executable.Daemon features.
"""

import logging
import pathlib
import time

import pytest

from lbr_testsuite.executable import executable, coredump, strace

from .conftest import match_syscalls


TESTING_OUTPUT = 'I am testing myself!'


def test_daemon_simple_args(helper_app):
    """Test successful execution of a simple command with arguments.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon([helper_app, '-f', '5', '-o', TESTING_OUTPUT, '-e', TESTING_OUTPUT])

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT
    assert stderr == TESTING_OUTPUT


def test_daemon_simple_args_str(helper_app):
    """Test successful execution of a simple command with arguments.

    Passing command as a string.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon(f'{helper_app} -f 5 -o "{TESTING_OUTPUT}" -e "{TESTING_OUTPUT}"')

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT
    assert stderr == TESTING_OUTPUT


def test_daemon_finished(helper_app):
    """Test successful execution of a simple command with arguments
    which ends before it is stopped.

    Passing command as a list of strings (preferred).

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon([helper_app, '-o', TESTING_OUTPUT, '-e', TESTING_OUTPUT])

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert not cmd.is_running()
    stdout, stderr = cmd.stop()

    assert stdout == TESTING_OUTPUT
    assert stderr == TESTING_OUTPUT


def test_daemon_simple_args_allowed_failure(helper_app):
    """Test of command which is allowed to fail.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon([helper_app, '-r', '2', '-e', TESTING_OUTPUT], failure_verbosity='no-exception')

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    stdout, stderr = cmd.stop()

    assert stdout == ''
    assert stderr == TESTING_OUTPUT


def test_daemon_simple_args_expected_failure(helper_app):
    """Test of command which is expected to fail.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon([helper_app, '-r', '2'], failure_verbosity='no-error')

    with pytest.raises(subprocess.CalledProcessError):
        cmd.start()
        time.sleep(1)  # wait some time so helper_app can register signal handlers
        cmd.stop()


def test_daemon_is_running(helper_app):
    """Test that running command check is working - running command.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    outputs_interval = 3
    outputs_multiplier = 2
    test_duration = outputs_multiplier * outputs_interval + 2
    cmd = executable.Daemon([helper_app, '-f', str(outputs_interval), '-o', TESTING_OUTPUT])

    cmd.start()
    time.sleep(test_duration)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    stdout, stderr = cmd.stop()
    assert not cmd.is_running()

    # TESTING_OUTPUT is printed right away and every outputs_interval second
    assert stdout == TESTING_OUTPUT * (1 + outputs_multiplier)
    assert stderr == ''


def test_daemon_not_running(helper_app):
    """Test that running command check is working - exited command.

    Parameters
    ----------
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Daemon([helper_app, '-o', TESTING_OUTPUT])

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert not cmd.is_running()
    stdout, stderr = cmd.stop()
    assert not cmd.is_running()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_daemon_coredump(tmp_files, helper_app):
    """Test that a failed command produces a coredump.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cd = coredump.Coredump()
    cd.set_output_file(tmp_files['core'])
    cmd = executable.Daemon([helper_app, '-f', '2', '-s'], default_logger_level=logging.CRITICAL + 1)
    cmd.set_coredump(cd)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can start and fail
    assert not cmd.is_running()
    with pytest.raises(subprocess.CalledProcessError, match='died with <Signals.SIGSEGV'):
        cmd.stop()

    assert pathlib.Path(cd.get_output_file()).exists()


def test_daemon_strace(tmp_files, helper_app):
    """Test that a commad produces a strace.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    st = strace.Strace()
    st.set_output_file(tmp_files['strace'])
    cmd = executable.Daemon([helper_app, '-f', '2'])
    cmd.set_strace(st)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can register signal handlers
    assert cmd.is_running()
    cmd.stop()

    assert pathlib.Path(st.get_output_file()).exists()


def test_daemon_strace_expressions_coredump(tmp_files, helper_app):
    """Test that a commad produces a strace with specified system calls
    only together with a coredump.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    strace_expressions = ('open', 'read')
    st = strace.Strace()
    st.set_output_file(tmp_files['strace'])
    st.add_expression(strace_expressions)
    cd = coredump.Coredump()
    cd.set_output_file(tmp_files['core'])
    cmd = executable.Daemon([helper_app, '-f', '2', '-s'], default_logger_level=logging.CRITICAL + 1)
    cmd.set_strace(st)
    cmd.set_coredump(cd)

    cmd.start()
    time.sleep(1)  # wait some time so helper_app can start and fail
    assert not cmd.is_running()
    with pytest.raises(subprocess.CalledProcessError, match='died with <Signals.SIGSEGV'):
        cmd.stop()

    assert pathlib.Path(st.get_output_file()).exists()
    assert pathlib.Path(cd.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions, segfault=True)
