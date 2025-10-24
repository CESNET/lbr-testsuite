"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

import logging

from .profiler import ProfiledSubject, Profiler


class MultiProfiler(Profiler):
    """
    Implementation of multi profiler that can control a number of
    other profiler instances.
    """

    def __init__(self, profilers):
        """
        Parameters
        ----------
        profilers : list
            List of profiler instances to be controlled.
        """

        self._profilers = profilers
        self._logger = logging.getLogger(type(self).__name__)

    def _stop_all(self, profilers):
        """Stop the given profilers in reverse order.

        Parameters
        ----------
        profilers : list
            List of profiler instances to be stopped.
        """

        for prof in reversed(profilers):
            try:
                self._logger.info(f"stopping profiler {prof}")
                prof.stop()
            except BaseException:
                self._logger.exception(f"failed to stop {prof}")

    def _join_all(self, profilers):
        """Wait on profilers in reverse order.

        Note: Profilers are passed explicitly as one does not to always
        want to join all profilers in self._profilers.

        Parameters
        ----------
        profilers : list
            List of profiler instances to be stopped.
        """

        for prof in reversed(profilers):
            try:
                self._logger.info(f"waiting on profiler {prof}")
                prof.join()
            except BaseException:
                self._logger.exception(f"failed to join {prof}")

    def start(self, subject: ProfiledSubject):
        """Start all underlying profilers. If any of them fails to start,
        stop them all and fail.
        """

        started = []

        for prof in self._profilers:
            try:
                self._logger.info(f"starting profiler {prof}")

                prof.start(subject)
                started.append(prof)
            except BaseException:
                self._stop_all(started)
                self._join_all(started)
                raise

    def stop(self):
        """Stop all underlying profilers."""

        self._stop_all(self._profilers)

    def join(self):
        """Wait until all underlying profilers finalize its work."""

        self._join_all(self._profilers)

    def mark(self, desc=None):
        """Call mark() on all underlying profilers."""

        for prof in self._profilers:
            prof.mark(desc)

    def postprocess_stored_data(self):
        for prof in self._profilers:
            prof.postprocess_stored_data()
