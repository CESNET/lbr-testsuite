"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Testing of executable module features. Common features of
executable.executable.Tool and executable.executable.Daemon (i.e.
features of parent executable.executable.Executable class) are tested
here. Also executable.coredump.Coredump, executable.strace.Strace
and specific executable.executable.Tool features are tested.
"""

import logging
import pathlib

import pytest
from lbr_testsuite.executable import executable, coredump, strace

from .conftest import match_syscalls


TESTING_OUTPUT = 'I am testing myself!'
NONEXISTING_FILE = 'I_expect_to_never_exist'


def _ls_err_message(file):
    return f'ls: cannot access {file}: No such file or directory\n'


def test_tool_simple():
    """Test successful execution of a simple command without arguments.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(['pwd'])

    stdout, stderr = cmd.run()

    assert len(stdout) > 0
    assert stderr == ''


def test_tool_simple_str():
    """Test successful execution of a simple command without arguments.

    Passing command as a string.
    """

    cmd = executable.Tool('pwd')

    stdout, stderr = cmd.run()

    assert len(stdout) > 0
    assert stderr == ''


def test_tool_simple_args():
    """Test successful execution of a simple command with arguments.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(['printf', TESTING_OUTPUT])

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_tool_simple_args_str():
    """Test successful execution of a simple command without arguments.

    Passing command as a string.
    """

    cmd = executable.Tool(f'printf "{TESTING_OUTPUT}"')

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_tool_simple_arg_append():
    """Test successful execution of a simple command with single
    appended argument.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(['printf'])
    cmd.append_arguments(TESTING_OUTPUT)

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_tool_simple_args_append_list():
    """Test successful execution of a simple command with argument
    appended as a list.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(['printf'])
    cmd.append_arguments([TESTING_OUTPUT])

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_tool_simple_arg_append_str():
    """Test successful execution of a simple command with single
    appended argument.

    Passing command as a string.
    """

    cmd = executable.Tool(f'printf')
    cmd.append_arguments(f' "{TESTING_OUTPUT}"')

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ''


def test_tool_simple_args_fail():
    """Test of simple command failure.

    Raising of subprocess.CalledProcessError exception is expected.
    """

    # Prevent logging of messages of any severity (i.e. all messages) from the testing command
    cmd = executable.Tool(['ls', NONEXISTING_FILE], default_logger_level=logging.CRITICAL + 1)

    with pytest.raises(subprocess.CalledProcessError):
        cmd.run()


def test_tool_simple_args_allowed_failure():
    """Test of command which is allowed to fail.
    """

    cmd = executable.Tool(['ls', NONEXISTING_FILE], allow_to_fail=True)

    stdout, stderr = cmd.run()

    assert stdout == ''
    assert stderr == _ls_err_message(NONEXISTING_FILE)


def test_tool_env():
    """Test of environment variable setup.
    """

    test_var = 'TEST_TOOL_ENV_VAR'
    test_var_value = TESTING_OUTPUT
    test_env = dict()
    test_env[test_var] = test_var_value
    cmd = executable.Tool(f'printf "${test_var}"', env=test_env)

    stdout, stderr = cmd.run()

    assert stdout == test_var_value
    assert stderr == ''


def test_tool_outputs_mixed(tmp_files, helper_app):
    """Test of outputs setting - stdout and stderr are mixed to a single
    file.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    cmd = executable.Tool([helper_app, '-o', TESTING_OUTPUT, '-e', TESTING_OUTPUT])
    cmd.set_outputs(str(tmp_files['stdout']))

    stdout, stderr = cmd.run()

    assert stdout is None and stderr is None
    assert tmp_files['stdout'].exists()
    with open(tmp_files['stdout'], 'r') as of:
        assert of.read() == f'{TESTING_OUTPUT}{TESTING_OUTPUT}'


def test_tool_outputs_separated(tmp_files, helper_app):
    """Test of outputs setting - stdout and stderr are separated to
    different files.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    """

    err_testing_output = f'err: {TESTING_OUTPUT}'
    cmd = executable.Tool([helper_app, '-o', TESTING_OUTPUT, '-e', err_testing_output])
    cmd.set_outputs(stdout=str(tmp_files['stdout']), stderr=str(tmp_files['stderr']))

    stdout, stderr = cmd.run()

    assert stdout is None and stderr is None
    assert tmp_files['stdout'].exists()
    assert tmp_files['stderr'].exists()
    with open(tmp_files['stdout'], 'r') as of:
        assert of.read() == TESTING_OUTPUT
    with open(tmp_files['stderr'], 'r') as of:
        assert of.read() == err_testing_output


def test_tool_coredump(tmp_files, helper_app):
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
    cmd = executable.Tool([helper_app, '-s'], default_logger_level=logging.CRITICAL + 1)
    cmd.set_coredump(cd)

    with pytest.raises(subprocess.CalledProcessError, match='died with <Signals.SIGSEGV'):
        cmd.run()

    assert pathlib.Path(cd.get_output_file()).exists()


def test_tool_strace(tmp_files):
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
    cmd = executable.Tool(['ls', '/'])
    cmd.set_strace(st)

    cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()


def test_tool_strace_expressions(tmp_files):
    """Test that a commad produces a strace with specified system calls
    only.

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
    cmd = executable.Tool(['ls', '/'])
    cmd.set_strace(st)

    cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions)


def test_tool_strace_expressions_coredump(tmp_files, helper_app):
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
    cmd = executable.Tool([helper_app, '-s'], default_logger_level=logging.CRITICAL + 1)
    cmd.set_strace(st)
    cmd.set_coredump(cd)

    with pytest.raises(subprocess.CalledProcessError, match='died with <Signals.SIGSEGV'):
        cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()
    assert pathlib.Path(cd.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions, segfault=True)
