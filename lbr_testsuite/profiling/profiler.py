"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

import collections
import logging
import pickle
import threading
from typing import TypeAlias

import pandas

from ..executable import executable


CollectedData: TypeAlias = tuple[pandas.DataFrame, any] | tuple[any]


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
        """Stop profiling and report profiling results in
        profiler-dependent way.
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

    def mark(self, desc=None):
        if self._profiler is not None:
            self._profiler.mark(desc)


class ThreadedProfiler(Profiler):
    """Abstract class that implements common profiler logic
    that runs as a Python code in thread.
    """

    def __init__(self, logger=None, output_file_base="./"):
        self._request_stop = True
        self._stopper = None

        if logger is None:
            self._logger = logging.getLogger(type(self).__name__)
        else:
            self._logger = logger

        self._output_file_base = output_file_base
        self._reserved_files = dict(
            csv=f"{self._format_file_name(output_file_base)}_raw.csv",
            raw=f"{self._format_file_name(output_file_base)}_raw",
            mark=f"{self._format_file_name(output_file_base)}_raw.mark",
        )
        self._marker = None

    @staticmethod
    def _format_file_name(file_name_base, *args):
        default_args = 100 * ("",)  # Fills empty strings for up to 100 arguments
        return str(file_name_base).format(*(args + default_args))

    def custom_file(self, suffix, *args):
        fn = f"{self._format_file_name(self._output_file_base, *args)}.{suffix}"
        assert (
            fn not in self._reserved_files.values()
        ), "Requested custom file may overwrite a reserved file"

        return fn

    def charts_file(self, *args):
        return f"{self._format_file_name(self._output_file_base, *args)}.html"

    def get_thread(self):
        """Get thread used for running this profiler."""

        return self._thread

    def start(self, subject: ProfiledSubject):
        """Start profiling thread."""

        self._subject = subject
        self._request_stop = False
        self._stopper = threading.Condition()

        self._marker = ProfilerMarker()

        def run_safe():
            try:
                self.run()
            except Exception:
                self._logger.exception(f"profiler {repr(self._subject)} has failed")

        self._thread = threading.Thread(target=run_safe, name=repr(self._subject))
        self._thread.start()

    def stop(self):
        """Request stop of the profiling thread."""

        if not self._stopper:
            return

        with self._stopper:
            self._request_stop = True
            self._stopper.notify_all()

    def should_stop(self):
        """
        Returns
        -------
        True when stop was requested, False otherwise
        """

        return self._request_stop

    def wait_stoppable(self, timeout):
        """Method can be used to stop executing the current thread for the
        specified timeout while being stoppable via method stop() without
        any delays.

        Returns
        -------
        True when stop was requested, False on timeout
        """

        with self._stopper:
            return self._stopper.wait_for(self.should_stop, timeout)

    def _data_collect(self) -> pandas.DataFrame | CollectedData:
        pass

    def _data_store(self, data: CollectedData):
        """Store data from data collection phase and marks (if any).

        There are three supported kinds of collected data:
        1) Data frame only,
        2) Data frame with some additional data,
        3) Custom data.

        Data frame is always saved as a csv file. Custom data is saved
        using pickle.dump method.
        """

        if isinstance(data[0], pandas.DataFrame):
            data[0].to_csv(self._reserved_files["csv"], index=False)
            data = data[1:]

        if data:
            with open(self._reserved_files["raw"], "wb") as out_f:
                pickle.dump(data, out_f)

        if self._marker:
            with open(self._reserved_files["mark"], "w") as f:
                self._marker.save(f)

    def _data_postprocess(self, *args):
        pass

    def run(self):
        """To be overriden by profiler implementation. Most of the time, the
        implementation would do something like:

            while not self.should_stop():
                do_something_useful()
        """

        data = self._data_collect()
        if not isinstance(data, tuple):
            data = (data,)

        self._data_store(data)

        self._data_postprocess(*data)


class PidProfiler(Profiler):
    """
    Abstract class that implements common profiler logic.
    """

    def __init__(self, cmd, logger=None, env=None):
        """
        Parameters
        ----------
        cmd : str, list or tuple
            Command to be used when executing the profiler.
        logger : logging.Logger(), optional
            Instance of logging.Logger class. If not set, class-specific
            logger is used.
        env : dict(), deprecated
            Mapping that defines environment variables for the profiler
            process.
        """

        if isinstance(cmd, list):
            self._cmd = cmd
        elif isinstance(cmd, tuple) or isinstance(cmd, str):
            self._cmd = list(cmd)
        else:
            raise RuntimeError(f"cmd is of unexpected type: {type(cmd)}")

        if logger is None:
            self._logger = logging.getLogger(type(self).__name__)
        else:
            self._logger = logger

        self._env = env
        self._daemon = None

    def _copy_cmd(self):
        """
        Returns
        -------
        list
            Copy of base command to start profiler.
        """
        return self._cmd.copy()

    def _build_cmd(self, pid):
        """Build command based on self._cmd, pid and possibly other
        profiler-dependent configuration. To be overriden by each
        implementation.

        Returns
        -------
        list
            Command to be executed as list of strings.
        """
        raise RuntimeError("_build_cmd() not implemented")

    def _create_daemon(self, cmd):
        """Create instance of Daemon that controls the profiler process.

        Returns
        -------
        executable.Daemon
            Instance of Daemon to be later executed.
        """

        return executable.Daemon(command=cmd, logger=self._logger, env=self._env)

    def start_pid(self, pid):
        """Creates daemon and starts it by using command generated by
        self._build_cmd(pid).
        """

        cmd = self._build_cmd(pid)
        self._logger.debug(f"starting profiler {cmd}")

        self._daemon = self._create_daemon(cmd)
        self._daemon.start()

    def start(self, subject: ProfiledSubject):
        """Start profiling the given subject

        Parameters
        ----------
        subject : ProfiledSubject
            Subject to be profiled.
        """

        if subject.has_pid():
            self.start_pid(subject.get_pid())
        else:
            raise Exception("failed to start profiling subject without PID")

    def stop(self):
        """Stop the underlying daemon if any."""

        if self._daemon:
            self._daemon.stop()
            self._daemon = None


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
                raise

    def stop(self):
        """Stop all underlying profilers."""

        self._stop_all(self._profilers)

    def mark(self, desc=None):
        """Call mark() on all underlying profilers."""

        for prof in self._profilers:
            prof.mark(desc)
