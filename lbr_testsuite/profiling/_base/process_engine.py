"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Concurrent engine using processes for execution of concurrent profilers.
"""

import multiprocessing as mp
from typing import Callable

from ...common import common
from .concurrent_engine import ConcurrentEngine


class ProcessEngine(ConcurrentEngine):
    """Concurrent engine using processes for execution of concurrent
    profilers.

    Using this engine, one can run profilers in separate sub-processes
    (one process per profiler). In python (because of GIL), this will
    probably produce better results than running profilers in separate
    threads.
    """

    def __init__(self, logger=None):
        super().__init__(logger)

        self._request_stop = None

    def start(self, run_fnc: Callable[[], None], identifier: str):

        self._request_stop = mp.Value("b", False)

        def run_safe():
            try:
                run_fnc()
            except Exception:
                self._logger.exception(f"profiler {identifier} has failed")

        self._process = mp.Process(target=run_safe, name=identifier)
        self._process.start()

    def stop(self):

        if self._request_stop is None:
            return

        self._request_stop.value = True

    def _should_stop(self) -> bool:
        """Check if stop was requested.

        Returns
        -------
        True when stop was requested, False otherwise.
        """

        return self._request_stop.value

    def wait_stoppable(self, timeout: float) -> bool:

        sleep_step = min(timeout / 10, 0.1)

        try:
            common.wait_until_condition(self._should_stop, timeout, sleep_step=sleep_step)
        except TimeoutError:
            pass

        return self._should_stop()
