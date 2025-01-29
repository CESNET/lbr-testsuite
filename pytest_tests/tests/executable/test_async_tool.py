"""
Author(s): Jan Sobol <sobol@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of executable module features. AsyncTool class.
"""

import time

import pytest

from lbr_testsuite import executable


TESTING_OUTPUT = "I am testing myself!\n"


def test_async_tool_wait(helper_app, testing_namespace, executor):
    """Test successful execution of a simple command with arguments.
    Command is awaited with wait_or_kill without timeout.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()
    stdout, _ = cmd.wait_or_kill()
    assert stdout == TESTING_OUTPUT


def test_async_tool_kill(helper_app, testing_namespace, executor):
    """Test execution of a simple command, which is killed.
    Non-zero return code is verified. Timeout parameter in
    wait_or_kill method is used.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
        failure_verbosity="no-error",
    )

    cmd.run()

    # kill after 1 second
    with pytest.raises(executable.ExecutableProcessError):
        cmd.wait_or_kill(timeout=1)

    assert cmd.returncode() != 0


def test_async_tool_continuous_read(helper_app, testing_namespace, executor):
    """Test of continuously reading stdout while command is running.
    Continuously is read only part of output, the rest should be returned
    by wait_or_kill method.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-f", "2", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
        # process is killed because is running forever (-f)
        failure_verbosity="silent",
    )

    cmd.run()

    # reading continuously part of the stdout
    ii = iter(cmd.stdout)
    for _ in range(3):
        assert next(ii) == TESTING_OUTPUT.strip()

    # timeout 6 seconds, rest of stdout should contain testing output 3 times
    rest_stdout, _ = cmd.wait_or_kill(timeout=6.1)

    assert rest_stdout == 3 * TESTING_OUTPUT


def test_async_tool_continuous_read_endls(helper_app, testing_namespace, executor):
    """Test of continuously reading stdout while command is running.
    Testing string contains endls (\n) inside. Iterators should return
    splitted string to lines.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-f", "2", "-o", 3 * TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
        # process is killed because is running forever (-f)
        failure_verbosity="silent",
    )

    cmd.run()

    # reading continuously part of the stdout
    # stdout is read by lines, one "flush" is splitted to 3 lines
    ii = iter(cmd.stdout)
    for _ in range(3):
        assert next(ii) == TESTING_OUTPUT.strip()

    rest_stdout, _ = cmd.wait_or_kill(timeout=2.1)

    assert rest_stdout == 3 * TESTING_OUTPUT


@pytest.mark.parametrize("blocks_count", [1, 2, 6])
def test_async_tool_continuous_read_long_line(
    helper_app, testing_namespace, executor, blocks_count
):
    """Test of continuously reading stdout while command is running.
    Testing string is longer than 1000 characters. The Fabric library
    used by RemoteExecutor flushes the output in blocks of 1000 characters.
    Iterator must connect these blocks.
    """

    # remote executor flushes blocks of 1000 characters
    testing_string = (blocks_count * 1000 + 1) * "x" + "\n"

    cmd = executable.AsyncTool(
        [helper_app, "-f", "2", "-o", testing_string],
        netns=testing_namespace,
        executor=executor,
        # process is killed because is running forever (-f)
        failure_verbosity="silent",
    )

    cmd.run()

    # reading continuously part of the stdout
    # stdout is read by lines, one "flush" is splitted to 3 lines
    ii = iter(cmd.stdout)
    assert next(ii) == testing_string.strip()

    rest_stdout, _ = cmd.wait_or_kill(timeout=2.1)

    assert rest_stdout == testing_string


@pytest.mark.parametrize("blocks_count", [1, 2, 6])
def test_async_tool_continuous_read_short_long_line(
    helper_app, testing_namespace, executor, blocks_count
):
    """Test of continuously reading stdout while command is running.
    Testing string is longer than 1000 characters. The Fabric library
    used by RemoteExecutor flushes the output in blocks of 1000 characters.
    Iterator must connect these blocks. Long lines alternate with short ones.
    """

    short_line = "short line\n"
    # remote executor flushes blocks of 1000 characters
    long_line = (blocks_count * 1000 + 1) * "x" + "\n"

    cmd = executable.AsyncTool(
        [helper_app, "-f", "2", "-o", short_line + long_line],
        netns=testing_namespace,
        executor=executor,
        # process is killed because is running forever (-f)
        failure_verbosity="silent",
    )

    cmd.run()

    # reading continuously part of the stdout
    # stdout is read by lines, one "flush" is splitted to 3 lines
    ii = iter(cmd.stdout)
    for _ in range(2):
        assert next(ii) == short_line.strip()
        assert next(ii) == long_line.strip()

    rest_stdout, _ = cmd.wait_or_kill(timeout=2.1)

    assert rest_stdout == short_line + long_line


def test_async_tool_continuous_read_wait(helper_app, testing_namespace, executor):
    """Test of continuously reading stdout while command is running.
    Reading output should block until command is not finished.
    The entire stdout is read, so stdout returned from wait_or_kill
    method should be empty.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-d", "2", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()

    # reading continuously since process finish
    lines = list(cmd.stdout)
    assert lines == [TESTING_OUTPUT.strip()]

    assert not cmd.is_running()

    rest_stdout, _ = cmd.wait_or_kill()
    assert rest_stdout == ""


def test_async_tool_repeated_wait(helper_app, testing_namespace, executor):
    """Test of repeated calls of wait_or_kill method.
    Returned stdout from each call should be identic.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()

    stdout, _ = cmd.wait_or_kill()
    assert stdout == TESTING_OUTPUT
    stdout2, _ = cmd.wait_or_kill()
    assert stdout2 == TESTING_OUTPUT


def test_async_tool_returncode_finished(helper_app, testing_namespace, executor):
    """Test of returncode method. Return code should be zero when
    command is successfully finished.
    """

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()
    assert cmd.returncode() is None

    cmd.wait_or_kill()
    assert cmd.returncode() == 0


def test_async_tool_returncode_expected_failure(helper_app, testing_namespace, executor):
    """Test of returncode method. Return code propagated from helper app
    should not be zero.
    """

    exp_retcode = 2

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT, "-r", str(exp_retcode)],
        netns=testing_namespace,
        executor=executor,
        failure_verbosity="no-error",
    )

    cmd.run()
    assert cmd.returncode() is None

    with pytest.raises(executable.ExecutableProcessError):
        cmd.wait_or_kill()

    assert cmd.returncode() == exp_retcode


def test_async_tool_is_running(helper_app, testing_namespace, executor):
    """Test of is_running method when command normally terminates."""

    cmd = executable.AsyncTool(
        [helper_app, "-d", "3", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
    )

    cmd.run()
    time.sleep(1)
    assert cmd.is_running()

    stdout, _ = cmd.wait_or_kill()
    assert not cmd.is_running()
    assert stdout == TESTING_OUTPUT


def test_async_tool_is_running_kill(helper_app, testing_namespace, executor):
    """Test of is_running method when command is killed."""

    cmd = executable.AsyncTool(
        [helper_app, "-f", "2", "-o", TESTING_OUTPUT],
        netns=testing_namespace,
        executor=executor,
        failure_verbosity="silent",
    )

    cmd.run()
    time.sleep(2)
    assert cmd.is_running()

    # kill after 1 second
    stdout, _ = cmd.wait_or_kill(timeout=1)

    assert not cmd.is_running()

    assert cmd.returncode() != 0
    assert stdout == 2 * TESTING_OUTPUT
