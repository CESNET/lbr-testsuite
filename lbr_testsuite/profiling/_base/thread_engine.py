"""
Author(s):
    Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Concurrent engine using threads for execution of concurrent profilers.
"""

import threading
from typing import Callable

from .concurrent_engine import ConcurrentEngine


class ThreadEngine(ConcurrentEngine):

    def __init__(self, logger=None):
        super().__init__(logger)

        self._request_stop = True
        self._stopper = None

    def start(self, run_fnc: Callable[[], None], identifier: str):

        self._request_stop = False
        self._stopper = threading.Condition()

        def run_safe():
            try:
                run_fnc()
            except Exception:
                self._logger.exception(f"profiler {identifier} has failed")

        self._process = threading.Thread(target=run_safe, name=identifier)
        self._process.start()

    def stop(self):

        if not self._stopper:
            return

        with self._stopper:
            self._request_stop = True
            self._stopper.notify_all()

    def _should_stop(self) -> bool:
        """Check if stop was requested.

        Returns
        -------
        True when stop was requested, False otherwise.
        """

        return self._request_stop

    def wait_stoppable(self, timeout: float) -> bool:

        with self._stopper:
            return self._stopper.wait_for(self._should_stop, timeout)
