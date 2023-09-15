"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Executor interface.

Provides interface that all executors must implement.

Executor executes/runs command and provides methods
to control and get status of launched command.
"""

from abc import ABC, abstractmethod


class OutputIterator(ABC):
    """Abstract base class for creating iterators to read the output (stdout or stderr)
    of a running process.

    Subclasses should implement the `__iter__` and `__next__` methods to define
    how the process output should be iterated and read.
    """

    @abstractmethod
    def __iter__(self):
        """Return the iterator object itself."""

        pass

    @abstractmethod
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

        pass


class Executor(ABC):
    """Executor interface.

    Executor executes/runs command and provides methods
    to control and get status of launched command.
    """

    @abstractmethod
    def get_process(self):
        """Get current process, last execution context.

        It is an object that is created when Executor runs
        command. Type of object depends on implementation of process
        execution. Executor can maintain only one process at one point
        in time. Process holds command context and could be used for
        futher handling in Executable.

        Returns
        -------
        any
            Returned process or None if process didn't start yet.
        """

        pass

    @abstractmethod
    def reset_process(self):
        """Reset process, prepare for new command execution.

        Set process to None.
        If executor contains process which is still running,
        then the process is stopped first.
        """

        pass

    def get_host(self):
        """Get name of host where executor is running.

        If local, it will be "localhost". For remote host it
        will be IP address or hostname.

        Returns
        -------
        str
            Host.
        """

        pass

    @abstractmethod
    def is_running(self):
        """Query if process is running.

        Returns
        -------
        bool
            True if process is running.
            False if process is not running.
        """

        pass

    @abstractmethod
    def terminate(self):
        """Terminate process. Process is interupted, method
        does not wait for the process to complete.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        pass

    @abstractmethod
    def wait(self):
        """Wait/block until process finishes.

        Raises
        ------
        RuntimeError
            If process doesn't exist yet (command was not run).
        """

        pass

    @abstractmethod
    def run(self, cmd, **options):
        """Run command.

        Parameters
        ----------
        cmd : str, list or tuple
            Command to run.
        options : dict, optional
            Optional arguments for run command.

        Returns
        -------
        any
            Launched process.
        """

        pass

    @abstractmethod
    def wait_or_kill(self, timeout=None):
        """Wait for process to finish within given timeout.

        If process fails to finish, it will be killed.

        Parameters
        ----------
        timeout : int, optional
            Timeout in seconds after which is process killed.

        Returns
        -------
        tuple(str, str)
            Tuple contaning 1) stdout and 2) stderr
            output from given process.
        """

        pass

    @abstractmethod
    def get_termination_status(self):
        """Get termination status of a process.

        Returns
        -------
        dict
            Dict with two keys - "rc" and "cmd".
            "rc" contains return code.
            "cmd" contains command that was used to run the process.
        """

        pass

    @abstractmethod
    def get_output_iterators(self):
        """Get iterators for stdout and stderr.

        Returns
        -------
        tuple(OutputIterator, OutputIterator)
            Tuple containing stdout and stderr iterator.
        """

        pass
