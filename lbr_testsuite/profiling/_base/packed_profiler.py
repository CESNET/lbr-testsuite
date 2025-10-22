"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

from .profiler import ProfiledSubject, Profiler


class PackedProfiler:
    """Profiler with packed subject. It is intentionally incompatible
    with Profiler class because its start() method cannot accept the
    subject at all.
    """

    def __init__(self, profiler: Profiler = None, subject: ProfiledSubject = None):
        """Construct PackedProfiler from a Profiler instance and subject.

        Parameters
        ----------
        profiler : Profiler, optional
            Profiler to be packed for profiling with the given subject.
        subject : ProfiledSubject, optional
            Subject to be profiled.
        """
        assert (
            subject is None and profiler is None
        ) or subject is not None, "if profiler is specified, subject must be given"

        self._profiler = profiler
        self._subject = subject

    def start(self):
        if self._profiler is not None:
            self._profiler.start(self._subject)

    def stop(self):
        if self._profiler is not None:
            self._profiler.stop()

    def join(self):
        if self._profiler is not None:
            self._profiler.join()

    def mark(self, desc=None):
        if self._profiler is not None:
            self._profiler.mark(desc)
