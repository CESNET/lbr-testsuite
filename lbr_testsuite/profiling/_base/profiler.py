"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

import collections

import pandas


class ProfiledSubject:
    def __init__(self, pid=None):
        self._pid = pid

    def has_pid(self):
        return self._pid is not None

    def get_pid(self):
        return self._pid

    def __repr__(self):
        if self.has_pid():
            return f"subject-{self._pid}"
        else:
            return super().__repr__()


class ProfilerMarker:
    """Generic implementation of call to Profiler.mark(). It collects all
    marks and finally allows to store them into file for post-processing.
    """

    Mark = collections.namedtuple("Mark", "time, desc")
    DEFAULT_DESC = ""

    def __init__(self, marks=None):
        self._marks = [] if marks is None else marks

    def mark(self, mark_time, desc=None):
        """
        Record a mark of the measurement.

        Parameters
        ----------
        mark_time: Any
            The argument is any arbitrary value that makes sense in
            the context of the calling profiler. It should be usually
            a time point on the profiler timeline taken from some
            monotonic time source.
        desc: str, optional
            Additional description of the marked event. It should be
            reasonably short (around 15 characters max).
        """

        d = desc if desc is not None else self.DEFAULT_DESC
        self._marks.append(self.Mark(mark_time, d))

    def __iter__(self):
        return iter(self._marks)

    def __len__(self):
        return len(self._marks)

    def save(self, f):
        """Save marks into the given file.

        Parameters
        ----------
        f: io.TextIOWrapper
            Opened file handler where marks should be stored.
        """

        for m in self._marks:
            print(f"{m.time},{m.desc}", file=f)

    @staticmethod
    def load(f, parse_line=float, parse_time=None):
        """Load marks from the given file and construct new instance of
        ProfilerMarker.

        Each line of the file should contain a single mark.

        Parameters
        ----------
        f: io.TextIOWrapper
            Opened file handler where marks should be stored.
        parse_line: callable, DEPRECATED
            A callback function used for parsing line value.
            The argument is deprecated as optional description were
            added to marks. Use `parse_time` instead.
        parse_time: callable, optional
            A callback function used for parsing time value of a single
            mark.
        """

        if not parse_time:
            parse_time = parse_line

        marker = ProfilerMarker()

        for line in f.readlines():
            time, desc = line.split(",")
            marker.mark(parse_time(time), desc.strip())

        return marker

    def to_dataframe(self):
        return pandas.DataFrame(
            dict(
                time=[m.time for m in self._marks],
                desc=[m.desc for m in self._marks],
            )
        )


class Profiler:
    """
    Interface to be implemented by a profiler implementation.
    """

    def start(self, subject: ProfiledSubject):
        """Start profiling the given subject

        Parameters
        ----------
        subject : ProfiledSubject
            Subject to be profiled.
        """
        pass

    def stop(self):
        """Stop profiling. Do not wait for profiler termination."""
        pass

    def join(self):
        """Wait for profiler to finalize its work. Report profiling
        results in profiler-dependent way.
        """
        pass

    def mark(self, desc=None):
        """Place a marker into the current time point. The marker would be
        used when generating visual outputs from the profiling. If a profiler
        does not work with any timeline, this call would be a no-op.
        """
        pass

    @staticmethod
    def _make_timestamps_relative(timestamps: pandas.Series, lowest=None):
        if not lowest:
            lowest = timestamps.min()
        return timestamps.sub(lowest).add(1).round(2).astype("float")
