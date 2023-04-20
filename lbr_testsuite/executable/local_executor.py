"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Local executor.

Implement local command execution via subprocess module.
"""

import subprocess

import pyroute2

from .executor import Executor


class LocalExecutor(Executor):
    """Implement local command execution via subprocess module."""

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
    def _prepend_sudo_to_command(cmd):
        if isinstance(cmd, str):
            cmd = "sudo " + cmd
        elif isinstance(cmd, list):
            cmd = ["sudo"] + cmd
        elif isinstance(cmd, tuple):
            cmd = ("sudo",) + cmd

        return cmd

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
            self._process = pyroute2.NSPopen(netns, cmd, **options)
        else:
            self._process = subprocess.Popen(cmd, **options)

    def wait_or_kill(self, timeout=None):
        """Wait for process to finish within given timeout.

        If process fails to finish, it will be killed.

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
