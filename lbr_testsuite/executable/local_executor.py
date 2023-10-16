"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Local executor.

Implement local command execution via subprocess module.
"""

import subprocess

from .executor import Executor, OutputIterator


class LocalExecutor(Executor):
    """Implement local command execution via subprocess module."""

    class LocalOutputIterator(OutputIterator):
        """Class for creating iterators to read the output (stdout or stderr)
        of a running process.
        """

        def __init__(self, executor, output_type):
            """Initialize iterator.

            Parameters
            ----------
            executor : LocalExecutor
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

        def __iter__(self):
            """Return the iterator object itself."""

            if not self._executor.is_running():
                raise RuntimeError("Cannot read output of non-running process.")

            if self._stdout:
                self._lines = iter(self._executor.get_process().stdout)
            else:
                self._lines = iter(self._executor.get_process().stderr)
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

            if not self._executor.is_running():
                raise StopIteration

            return next(self._lines).strip()

    def __init__(self):
        self._process = None
        self._used_sudo = False

    def get_process(self):
        """Get current process, last execution context.

        It is an object that is created when Executor runs
        command. Type of object depends on implementation of process
        execution. Executor can maintain only one process at one point
        in time. Process holds command context and could be used for
        futher handling in Executable.

        Returns
        -------
        subprocess.Popen or None
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

    def get_host(self):
        """Get name of host where executor is running.

        If local, it will be "localhost". For remote host it
        will be IP address or hostname.

        Returns
        -------
        str
            Host.
        """

        return "localhost"

    def is_running(self):
        """Query if process is running.

        Returns
        -------
        bool
            True if process is running.
            False if process is not running.
        """

        if not self._process:
            return False

        return self._process.poll() is None

    def terminate(self):
        """Terminate process. Process is interupted, method
        does not wait for the process to complete.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if not self._process:
            raise RuntimeError("Process was not started yet")

        if self._used_sudo:
            # In case process was started with explicit sudo prefix
            subprocess.run(
                f"sudo kill -s SIGTERM {self._process.pid}",
                shell=True,
                check=True,
            )
        else:
            self._process.terminate()

    def wait(self):
        """Wait/block until process finishes.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if not self._process:
            raise RuntimeError("Process was not started yet")

        self._process.wait()

    @staticmethod
    def _prepend_to_command(prepend, cmd):
        if isinstance(cmd, str):
            cmd = f"{prepend} {cmd}"
        elif isinstance(cmd, list):
            prepend = prepend.split()
            cmd = prepend + cmd
        elif isinstance(cmd, tuple):
            prepend = tuple(prepend.split())
            cmd = prepend + cmd

        return cmd

    @staticmethod
    def _prepend_sudo_to_command(cmd):
        return LocalExecutor._prepend_to_command("sudo", cmd)

    @staticmethod
    def _prepend_netns_to_command(cmd, netns):
        ip_path = "/usr/sbin/ip"
        return LocalExecutor._prepend_to_command(f"{ip_path} netns exec {netns}", cmd)

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
            Optional arguments for run command, specifically
            options for subprocess.Popen() object.
        """

        self._used_sudo = sudo

        if sudo:
            cmd = self._prepend_sudo_to_command(cmd)

        if netns:
            cmd = self._prepend_netns_to_command(cmd, netns)

        self._process = subprocess.Popen(cmd, **options)

    def wait_or_kill(self, timeout=None):
        """Wait for process to finish within given timeout.

        If process fails to finish, it will be killed.

        Note: None timeout can make it impossible to read the outputs repeatedly
        (communicate method). Therefore, None is converted to a very long timeout.

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

        if timeout is None:
            timeout = 1e6

        if not self._process:
            raise RuntimeError("Process was not started yet")

        try:
            """Note from subprocess documentation:
            This will deadlock when using stdout=PIPE or stderr=PIPE
            and the child process generates enough output to a pipe
            such that it blocks waiting for the OS pipe buffer to accept
            more data. Use Popen.communicate() when using pipes to
            avoid that.
            """
            stdout, stderr = self._process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                self._process.kill()
            except PermissionError:
                if self._used_sudo:
                    # In case process was started with explicit sudo prefix
                    subprocess.run(
                        f"sudo kill -s SIGKILL {self._process.pid}",
                        shell=True,
                        check=True,
                    )
                else:
                    raise

            stdout, stderr = self._process.communicate()

        return stdout, stderr

    def get_termination_status(self):
        """Get termination status of a process.

        Returns
        -------
        dict
            Dict with two keys - "rc" and "cmd".
            "rc" contains return code.
            "cmd" contains command that was used to run the process.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        if not self._process:
            raise RuntimeError("Process was not started")

        return {
            "rc": self._process.returncode,
            "cmd": self._process.args,
        }

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
            self.LocalOutputIterator(self, "stdout"),
            self.LocalOutputIterator(self, "stderr"),
        )
