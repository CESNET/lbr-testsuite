"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Testing of executable module features. Common features of
executable.executable.Tool and executable.executable.Daemon (i.e.
features of parent executable.executable.Executable class) are tested
here. Also executable.coredump.Coredump, executable.strace.Strace
and specific executable.executable.Tool features are tested.
"""

import logging
import pathlib
import subprocess

import pytest

from lbr_testsuite.executable import coredump, executable, strace
from lbr_testsuite.executable.local_executor import LocalExecutor
from lbr_testsuite.executable.remote_executor import RemoteExecutor

from .conftest import match_syscalls


TESTING_OUTPUT = "I am testing myself!"


def test_tool_simple(testing_namespace, executor):
    """Test successful execution of a simple command without arguments.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(["pwd"], netns=testing_namespace, executor=executor)

    stdout, stderr = cmd.run()

    assert len(stdout) > 0
    assert stderr == ""


def test_tool_simple_str(testing_namespace, executor):
    """Test successful execution of a simple command without arguments.

    Passing command as a string.
    """

    cmd = executable.Tool("pwd", executor=executor)

    stdout, stderr = cmd.run()

    assert len(stdout) > 0
    assert stderr == ""


def test_tool_simple_args(testing_namespace, executor):
    """Test successful execution of a simple command with arguments.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(["printf", TESTING_OUTPUT], netns=testing_namespace, executor=executor)

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_args_str(testing_namespace, executor):
    """Test successful execution of a simple command without arguments.

    Passing command as a string.
    """

    cmd = executable.Tool(f'printf "{TESTING_OUTPUT}"', netns=testing_namespace, executor=executor)

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_arg_append(testing_namespace, executor):
    """Test successful execution of a simple command with single
    appended argument.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(["printf"], netns=testing_namespace, executor=executor)
    cmd.append_arguments(TESTING_OUTPUT)

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_args_append_list(testing_namespace, executor):
    """Test successful execution of a simple command with argument
    appended as a list.

    Passing command as a list of strings (preferred).
    """

    cmd = executable.Tool(["printf"], netns=testing_namespace, executor=executor)
    cmd.append_arguments([TESTING_OUTPUT])

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_arg_append_str(testing_namespace, executor):
    """Test successful execution of a simple command with single
    appended argument.

    Passing command as a string.
    """

    cmd = executable.Tool(f"printf", netns=testing_namespace, executor=executor)
    cmd.append_arguments(f' "{TESTING_OUTPUT}"')

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_args_fail(helper_app, testing_namespace, executor):
    """Test of simple command failure.

    Raising of executable.ExecutableProcessError exception is expected.
    """

    # Prevent logging of messages of any severity (i.e. all messages) from the testing command
    cmd = executable.Tool(
        [helper_app, "-r", "2"],
        default_logger_level=logging.CRITICAL + 1,
        netns=testing_namespace,
        executor=executor,
    )

    with pytest.raises(executable.ExecutableProcessError):
        cmd.run()


def test_tool_simple_args_allowed_failure(helper_app, testing_namespace, executor):
    """Test of command which is allowed to fail."""

    cmd = executable.Tool(
        [helper_app, "-r", "2", "-e", TESTING_OUTPUT],
        failure_verbosity="no-exception",
        netns=testing_namespace,
        executor=executor,
    )

    stdout, stderr = cmd.run()

    assert stdout == TESTING_OUTPUT
    assert stderr == ""


def test_tool_simple_args_expected_failure(helper_app, testing_namespace, executor):
    """Test of command which is expected to fail."""

    cmd = executable.Tool(
        [helper_app, "-r", "2"],
        failure_verbosity="no-error",
        netns=testing_namespace,
        executor=executor,
    )

    with pytest.raises(executable.ExecutableProcessError):
        cmd.run()


def test_tool_returncode_none(helper_app, testing_namespace, executor):
    """Test that return code is None when executable was not started."""

    cmd = executable.Tool(
        [helper_app],
        netns=testing_namespace,
        executor=executor,
    )

    assert cmd.returncode() is None


def test_tool_returncode_ok(helper_app, testing_namespace, executor):
    """Test that return code is None when executable was not started."""

    cmd = executable.Tool(
        [helper_app],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()

    assert cmd.returncode() == 0


def test_tool_returncode_repeatable(helper_app, testing_namespace, executor):
    """Test that return code is accessible repeatedly."""

    cmd = executable.Tool(
        [helper_app],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()

    assert cmd.returncode() == 0
    assert cmd.returncode() == 0


def test_tool_returncode_expected_failure(helper_app, testing_namespace, executor):
    """Test return code of a command which is expected to fail."""

    exp_retcode = 2

    cmd = executable.Tool(
        [helper_app, "-r", str(exp_retcode)],
        failure_verbosity="no-error",
        netns=testing_namespace,
        executor=executor,
    )

    with pytest.raises(executable.ExecutableProcessError):
        cmd.run()

    assert cmd.returncode() == exp_retcode


def test_tool_returncode_allowed_failure(helper_app, testing_namespace, executor):
    """Test return code of a command which is expected to fail."""

    exp_retcode = 2

    cmd = executable.Tool(
        [helper_app, "-r", str(exp_retcode)],
        failure_verbosity="no-exception",
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()

    assert cmd.returncode() == exp_retcode


def test_tool_env(testing_namespace, executor):
    """Test of environment variable setup."""

    if isinstance(executor, RemoteExecutor):
        pytest.skip(f"remote executor does work differently with env")

    test_var = "TEST_TOOL_ENV_VAR"
    test_var_value = TESTING_OUTPUT
    test_env = dict()
    test_env[test_var] = test_var_value
    cmd = executable.Tool(["printenv", "-0"], netns=testing_namespace, executor=executor)
    cmd.set_env(test_env)

    stdout, stderr = cmd.run()

    expected_output = f"{test_var}={test_var_value}\x00"
    assert stdout == expected_output
    assert stderr == ""


def test_tool_env_key(testing_namespace, executor):
    """Test of environment variable setup."""

    test_var = "TEST_TOOL_ENV_VAR"
    test_var_value = TESTING_OUTPUT
    cmd = executable.Tool(f'printf "${test_var}"', netns=testing_namespace, executor=executor)
    cmd.set_env_key(test_var, test_var_value)

    stdout, stderr = cmd.run()

    assert stdout == test_var_value
    assert stderr == ""


def test_tool_env_clear(testing_namespace, executor):
    """Test of environment variable setup."""

    if isinstance(executor, RemoteExecutor):
        pytest.skip(f"remote executor does work differently with env")

    cmd = executable.Tool(["printenv", "-0"], netns=testing_namespace, executor=executor)
    cmd.clear_env()

    stdout, stderr = cmd.run()

    assert stdout == ""
    assert stderr == ""


def test_tool_cwd(tmp_path, testing_namespace, executor):
    """Test of command current working directory (cwd) setup."""

    cmd = executable.Tool(["pwd"], netns=testing_namespace, executor=executor)
    cmd.set_cwd(tmp_path)

    stdout, stderr = cmd.run()

    assert stdout == f"{tmp_path}\n"
    assert stderr == ""


def test_tool_outputs_mixed(tmp_files, helper_app, testing_namespace, executor):
    """Test of outputs setting - stdout and stderr are mixed to a single
    file.

    Parameters
    ----------
    tmp_files : dict(Path)
        Paths to temporary output paths.
    helper_app : str
        Path to the testing helper application in a form of string.
    executor : executable.Executor
        Executor to use.
    """

    cmd = executable.Tool(
        [helper_app, "-o", TESTING_OUTPUT, "-e", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_outputs(str(tmp_files["stdout"]))

    stdout, stderr = cmd.run()

    assert stdout == "" and stderr == ""
    assert tmp_files["stdout"].exists()
    with open(tmp_files["stdout"], "r") as of:
        assert of.read() == f"{TESTING_OUTPUT}{TESTING_OUTPUT}"


def test_tool_outputs_separated(tmp_files, helper_app, testing_namespace, executor):
    """Test of outputs setting - stdout and stderr are separated to
    different files.

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
        pytest.skip(f"remote executor does not support setting stderr")

    err_testing_output = f"err: {TESTING_OUTPUT}"
    cmd = executable.Tool(
        [helper_app, "-o", TESTING_OUTPUT, "-e", err_testing_output],
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_outputs(stdout=str(tmp_files["stdout"]), stderr=str(tmp_files["stderr"]))

    stdout, stderr = cmd.run()

    assert stdout == "" and stderr == ""
    assert tmp_files["stdout"].exists()
    assert tmp_files["stderr"].exists()
    with open(tmp_files["stdout"], "r") as of:
        if isinstance(executor, LocalExecutor):
            assert of.read() == TESTING_OUTPUT
        else:
            assert of.read() == err_testing_output + TESTING_OUTPUT

    with open(tmp_files["stderr"], "r") as of:
        if isinstance(executor, LocalExecutor):
            assert of.read() == err_testing_output
        else:
            assert of.read() == ""


def test_tool_coredump(require_root, tmp_files, helper_app, testing_namespace, executor):
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
    cmd = executable.Tool(
        [helper_app, "-s"],
        default_logger_level=logging.CRITICAL + 1,
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_coredump(cd)

    with pytest.raises(executable.ExecutableProcessError, match="died with <Signals.SIGSEGV"):
        cmd.run()

    assert pathlib.Path(cd.get_output_file()).exists()


def test_tool_strace(tmp_files, testing_namespace, executor):
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
    cmd = executable.Tool(["ls", "/"], netns=testing_namespace, executor=executor)
    cmd.set_strace(st)

    cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()


def test_tool_strace_expressions(tmp_files, testing_namespace, executor):
    """Test that a commad produces a strace with specified system calls
    only.

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

    strace_expressions = ("open", "read")
    st = strace.Strace()
    st.set_output_file(tmp_files["strace"])
    st.add_expression(strace_expressions)
    cmd = executable.Tool(["ls", "/"], netns=testing_namespace, executor=executor)
    cmd.set_strace(st)

    cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions)


def test_tool_strace_expressions_coredump(
    require_root,
    tmp_files,
    helper_app,
    testing_namespace,
    executor,
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
    cmd = executable.Tool(
        [helper_app, "-s"],
        default_logger_level=logging.CRITICAL + 1,
        netns=testing_namespace,
        executor=executor,
    )
    cmd.set_strace(st)
    cmd.set_coredump(cd)

    with pytest.raises(executable.ExecutableProcessError, match="died with <Signals.SIGSEGV"):
        cmd.run()

    assert pathlib.Path(st.get_output_file()).exists()
    assert pathlib.Path(cd.get_output_file()).exists()
    assert match_syscalls(st.get_output_file(), strace_expressions, segfault=True)


def test_tool_repeated_single_instance(testing_namespace, executor):
    """Test that Tool object can call the 'run()' method repeatedly
    without any errors. This tests correct garbage cleanup by the
    executable module.

    Parameters
    ----------
    testing_namespace : str
        Namespace to run commands in.
    executor : executable.Executor
        Executor to use.
    """

    repeat_count = 500

    cmd = executable.Tool(["pwd"], netns=testing_namespace, executor=executor)

    for i in range(repeat_count):
        stdout, stderr = cmd.run()

        assert len(stdout) > 0
        assert stderr == ""


def test_tool_repeated_individual_instances(testing_namespace, executor):
    """Test that Tool object can be constructed multiple times.
    This tests correct garbage collection when objects are created
    repeatedly.

    Parameters
    ----------
    testing_namespace : str
        Namespace to run commands in.
    executor : executable.Executor
        Executor to use.
    """

    repeat_count = 500

    for i in range(repeat_count):
        cmd = executable.Tool(["pwd"], netns=testing_namespace, executor=executor)
        stdout, stderr = cmd.run()

        assert len(stdout) > 0
        assert stderr == ""
