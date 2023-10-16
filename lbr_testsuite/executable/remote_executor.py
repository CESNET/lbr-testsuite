"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Remote executor.

Implement remote command execution via fabric module.
"""

import io
import logging
import os
import shlex
import subprocess
import time

import fabric
import invoke

from .. import common
from .executor import Executor, OutputIterator


def ssh_agent_enabled():
    """Check if SSH agent is enabled and running.

    This is done by checking if ``SSH_AUTH_SOCK``
    environment variable exists.

    Returns
    -------
    bool
        True if SSH agent is enabled and running.
    """

    if os.getenv("SSH_AUTH_SOCK") is not None:
        return True

    return False


class RemoteExecutor(Executor):
    """Implement remote command execution via fabric module.

    Parameters
    ----------
    host : str
        Host where commands will be executed.
        Can be hostname or IP address.
    user : str, optional
        Login user for the remote connection.
        If ``password`` or ``key_filename`` is not
        provided, use SSH agent for authentication.
    password : str, optional
        Password for ``user``.
        Has higher priority than ``key_filename``.
    key_filename : str, optional
        Path to private key(s) and/or certs.
        Key must *not* be encrypted (must be
        without password).

    Raises
    ------
    EnvironmentError
        SSH agent is not enabled.
        SSH agent is required only if ``password`` or
        ``key_filename`` is not provided.
    """

    class RemoteOutputIterator(OutputIterator):
        """Class for creating iterators to read the output (stdout or stderr)
        of a running process.
        """

        def __init__(self, executor, output_type):
            """Initialize iterator.

            Parameters
            ----------
            executor : RemoteExecutor
                Executor with process from which the output is read.
            output_type : str
                "stdout" or "stderr"

            Raises
            ------
            AssertionError
                When output_type is not standard output (stdout, stderr).
            """

            assert output_type in ["stdout", "stderr"]

            self._executor = executor
            self._stdout = output_type == "stdout"
            self._lines = None
            self._buffer = []

        @staticmethod
        def _process_line(line):
            line = line.replace("^C", "")
            line = line.strip()
            return line

        @staticmethod
        def _ends_endl(line):
            return line.endswith("\n") or line.endswith("\r\n")

        def __iter__(self):
            """Return the iterator object itself."""

            if not self._executor.is_running():
                raise RuntimeError("Cannot read output of non-running process.")

            if self._stdout:
                self._lines = self._executor.get_process().runner.stdout
            else:
                self._lines = self._executor.get_process().runner.stderr
            return self

        def __next__(self):
            """Retrieve the next line of output from the process.
            Method blocks until the line is read or the process
            is terminated.

            Returns
            -------
            str
                The next line of output as a string.

            Raises
            ------
            StopIteration
                When process ended.
            """

            while True:
                if len(self._buffer) > 0 and self._ends_endl(self._buffer[0]):
                    return self._process_line(self._buffer.pop(0))

                if not self._executor.is_running():
                    raise StopIteration

                if len(self._lines) > 0:
                    lines = io.StringIO(self._lines.pop(0)).readlines()

                    if len(self._buffer) > 0:
                        # append to discontinued line from last read
                        self._buffer[0] += lines[0]
                        self._buffer += lines[1:]
                    else:
                        self._buffer.extend(lines)

                time.sleep(0.1)

    def __init__(
        self,
        host,
        user=common.get_real_user(),
        password=None,
        key_filename=None,
    ):
        self._process = None
        self._result = None
        connect_kwargs = {}

        if password is not None:
            connect_kwargs["password"] = password
            connect_kwargs["allow_agent"] = False
            connect_kwargs["look_for_keys"] = False
        elif key_filename is not None:
            connect_kwargs["key_filename"] = key_filename
        elif not ssh_agent_enabled():
            logging.getLogger().error(
                "SSH agent must be enabled when other authentication methods are not provided."
            )
            raise EnvironmentError(
                "SSH agent must be enabled when other authentication methods are not provided."
            )

        self._host = host

        self._connection = fabric.Connection(
            host=host,
            user=user,
            connect_kwargs=connect_kwargs,
        )
        self._connection.open()

    def get_process(self):
        """Get current process, last execution context.

        It is an object that is created when Executor runs
        command. Type of object depends on implementation of process
        execution. Executor can maintain only one process at one point
        in time. Process holds command context and could be used for
        futher handling in Executable.

        Returns
        -------
        invoke.runners.Promise or None
            Returned process or None if process didn't start yet.
        """

        return self._process

    def reset_process(self):
        """Reset process, prepare for new command execution.

        Set process to None.
        If executor contains process which is still running,
        then the process is stopped first.
        """

        if self.is_running():
            self.terminate()
            self.wait_or_kill(1)

        self._process = None
        self._result = None

    def get_host(self):
        """Get name of host where executor is running.

        If local, it will be "localhost". For remote host it
        will be IP address or hostname.

        Returns
        -------
        str
            Host.
        """

        return self._host

    def close(self):
        """Close fabric (SSH) connection to host."""

        self._connection.close()

    def get_connection(self):
        """Get connection object.

        Used to retrieve user and connection kwargs to custom handling (rsync).

        Returns
        -------
        fabric.connection.Connection
            Connection object.
        """

        return self._connection

    def is_running(self):
        """Query if process is running.

        Returns
        -------
        bool
            True if process is running, False otherwise.
        """

        if self._process is None:
            return False

        # Official wait() implementation
        # https://github.com/pyinvoke/invoke/blob/main/invoke/runners.py#L990
        # also checks for process.runner.has_dead_threads
        # Probably not needed here.
        return not self._process.runner.process_is_finished

    def terminate(self):
        """Terminate process. Process is interupted, method
        does not wait for the process to complete.

        Note that this sends SIGINT (CTRL+C) to process.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if self._process is None:
            raise RuntimeError("Process was not started yet")

        try:
            # Works only if run() has pty=True, otherwise it does nothing
            # See https://github.com/fabric/fabric/blob/3.0.0/fabric/runners.py#L93
            self._process.runner.send_interrupt(KeyboardInterrupt)
        except OSError as err:
            # If process already finished, "Socket is closed"
            # error is raised as system can't send signal to
            # already finished process.
            if err.args[0] == "Socket is closed":
                pass
            else:
                raise

    def wait(self):
        """Wait/block until process finishes.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if self._process is None:
            raise RuntimeError("Process was not started yet")

        self._process.runner.wait()

    def run(self, cmd, netns=None, sudo=False, **options):
        """Run command.

        Parameters
        ----------
        cmd : str, list or tuple
            Command to run.
        netns : str, optional
            Network namespace name. If set, a command is executed in
            a namespace using the "ip netns" command.
        sudo : bool, optional
            Run command with sudo.
        options : dict, optional
            Optional arguments for run command.
            See executable.Executable for more info.
        """

        if self._process is not None:
            raise RuntimeError(
                "The previous process is running or the executor has not been reset."
            )

        use_sudo = False

        # Convert to string
        if isinstance(cmd, list):
            cmd = shlex.join(cmd)

        if os.geteuid() == 0 or sudo:
            use_sudo = True

        if netns:
            cmd = f"ip netns exec {netns} {cmd}"

        if "cwd" in options:
            cmd = f"cd {options['cwd']} && {cmd}"
            mkdir = f"mkdir -p {options['cwd']}"
            if use_sudo:
                self._connection.run(f"sudo {mkdir}")
            else:
                self._connection.run(f"{mkdir}")

        if use_sudo:
            # https://stackoverflow.com/questions/1250079/how-to-escape-single-quotes-within-single-quoted-strings#comment66009022_12502
            # Replace ' with '\'' inside command
            # Use \\ instead of single \ as Python interprets it as an escape character
            cmd = cmd.replace("'", "'\\''")
            cmd = f"sudo -E sh -c '{cmd}'"

        out_stream = None
        err_stream = None

        # Try to mimic LocalExecutor behaviour.
        # RemoteExecutor doesn't support PIPE.
        # Works only if pty=False, otherwise
        # stdout and stderr are mixed into stdout.
        if options["stdout"] != subprocess.PIPE:
            out_stream = options["stdout"]

        if options["stderr"] != subprocess.PIPE:
            if options["stderr"] == subprocess.STDOUT:
                err_stream = out_stream  # redirect to stdout stream, mimic LocalExecutor
            else:
                err_stream = options["stderr"]

        # Env string variables need to be quoted
        # as they can contain spaces etc..
        #
        # Note: paramiko inherits environment (see
        # https://docs.paramiko.org/en/stable/api/channel.html#paramiko.channel.Channel.update_environment),
        # This differs from subprocess, which starts
        # with empty environment, meaning that commands like
        # "env" or "printenv" will have different outputs
        # when run in local or remote executor
        env = options["env"]
        if env is not None:
            for k, v in env.items():
                if isinstance(v, str):
                    env[k] = shlex.quote(v)

        self._process = self._connection.run(
            cmd,
            asynchronous=True,
            encoding=options["encoding"],
            out_stream=out_stream,
            err_stream=err_stream,
            env=env,
            # pty=True means stdout and stderr is mixed.
            # pty=False means that process cannot be properly
            # terminated (see terminate()).
            pty=True,
        )

    def wait_or_kill(self, timeout=1e9):
        """Wait for process to finish within given timeout.

        If process fails to finish, method will attempt to
        terminate it. Note that in remote execution there
        seems no easy way will send SIGKILL, so stubborn
        process can potentially keep running on the remote
        host.

        Parameters
        ----------
        timeout : float, optional
            Timeout in seconds.

        Returns
        -------
        tuple(str, str)
            Tuple contaning 1) stdout and 2) stderr
            output from given process.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if self._process is None:
            raise RuntimeError("Process was not started yet")

        def _process_finished():
            return self._process.runner.process_is_finished

        # As local executor accepts None, convert None to number
        if timeout is None:
            timeout = 1e9

        if not common.wait_until_condition(_process_finished, timeout=timeout):
            self.terminate()
            self._process.runner.kill()

        finished = self._join_process()

        stdout = finished.stdout
        stderr = finished.stderr

        # Replace network newlines to unix newlines
        stdout = stdout.replace("\r\n", "\n")
        stderr = stderr.replace("\r\n", "\n")

        # Remove ^C at the end of text, which resulted from calling terminate()
        stdout = stdout.replace("^C", "")
        stderr = stderr.replace("^C", "")

        return stdout, stderr

    def get_termination_status(self):
        """Get termination status of a process.

        Returns
        -------
        dict
            Dict with two keys - "rc" and "cmd".
            "rc" contains return code.
            "cmd" contains command that was used to run the process.

            If process was killed by a signal, then real
            return code is not received. Instead, default
            return code -1 is returned. The reason is that
            paramiko module, which handles low-level SSH
            connection doesn't support "exit-signal" message
            yet. More information can be found at:
            https://github.com/paramiko/paramiko/issues/598

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if self._process is None:
            raise RuntimeError("Process was not started yet")

        result = self._join_process()
        return {"rc": result.exited, "cmd": result.command}

    def get_output_iterators(self):
        """Get iterators for stdout and stderr.

        Iterators are intended to be used only while the process is running.
        Reading output should be realized only by one instance of iterator.

        Note: each line which is read by iterator is removed from the final
        output (wait_or_kill method).

        Returns
        -------
        tuple(OutputIterator, OutputIterator)
            Tuple containing stdout and stderr iterator.
        """

        return (
            self.RemoteOutputIterator(self, "stdout"),
            self.RemoteOutputIterator(self, "stderr"),
        )

    def _join_process(self):
        """Wrapper for invoke process join. Prevents calling
        join method more than once.

        Process runner is finished and stopped while calling
        join method. Repeated call of join returns different
        result object.

        Returns
        -------
        invoke.runners.Result
            Result of process execution.
        """

        if self._result is None:
            try:
                self._result = self._process.join()
            except invoke.exceptions.UnexpectedExit as ee:
                self._result = ee.result

        return self._result
