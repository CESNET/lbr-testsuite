"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Abstract class for concurrent engine.

A concurrent engine is used by profiler for control of execution of
concurrent profilers.
"""

import logging
from typing import Callable


class ConcurrentEngine:
    """This class serves for control of execution of underlying
    process/thread/etc. (for simplicity, we will say just "process").

    Attributes
    ----------
    _logger: logging.Logger
        Logging facility used by the engine.
    _process: Any
        A representation of "process unit" (process, thread, ...).
    """

    def __init__(self, logger: logging.Logger = None):
        if logger is None:
            self._logger = logging.getLogger(type(self).__name__)
        else:
            self._logger = logger

        self._process = None

    def get_name(self) -> str:
        """Get name of the underlying process object."""

        return self._process.name

    def start(self, run_fnc: Callable[[], None], identifier: str):
        """Start the underlying process.

        Parameters
        ----------
        run_func: Callable[[], None]
            Main function which the process will be executing.
        identifier: str
            Process identification.
        """

        ...

    def stop(self):
        """Stop the process."""

        ...

    def join(self):
        """Wait for the process to finish."""

        if self._process:
            self._process.join()

    def wait_stoppable(self, timeout: float) -> bool:
        """Method can be used to stop execution of the current process
        for the specified timeout while still being stoppable via method
        stop() without any delays.

        Parameters
        ----------
        timeout: float
            For how long the process execution should be stopped (in
            seconds).

        Returns
        -------
        bool:
            True if stop has been requested, False on timeout.
        """

        ...
