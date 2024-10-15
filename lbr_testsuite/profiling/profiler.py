"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

import logging
import threading

import pandas

from ..executable import executable


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
    """
    Generic implementation of call to Profiler.mark(). It collects all
    marks and finally allows to store them into file for post-processing.
    """

    def __init__(self, marks=None):
        self._marks = [] if marks is None else marks

    def mark(self, mark_time):
        """
        Record a mark of the measurement. The argument mark_time is any arbitrary
        value that makes sense in the context of the calling profiler. It should
        be usually a time point on the profiler timeline taken from some monotonic
        time source.
        """

        self._marks.append(mark_time)

    def __iter__(self):
        return iter(self._marks)

    def save(self, f):
        """
        Save marks into the given file.
        """

        for m in self._marks:
            print(m, file=f)

    @staticmethod
    def load(f, parse_line=float):
        """
        Load marks from the given file and construct new instance of ProfilerMarker.
        Each line of the file should contain a single mark. Each line is parsed using
        the callback given as parse_line.
        """

        marks = []

        for line in f.readlines():
            marks.append(parse_line(line))

        return ProfilerMarker(marks)


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

    def mark(self):
        """Place a marker into the current time point. The marker would be
        used when generating visual outputs from the profiling. If a profiler
        does not work with any timeline, this call would be a no-op.
        """
        pass

    @staticmethod
    def _make_timestamps_relative(timestamps: pandas.Series):
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

    def mark(self):
        if self._profiler is not None:
            self._profiler.mark()


class ThreadedProfiler(Profiler):
    """Abstract class that implements common profiler logic
    that runs as a Python code in thread.
    """

    def __init__(self, logger=None):
        self._request_stop = True
        self._stopper = None

        if logger is None:
            self._logger = logging.getLogger(type(self).__name__)
        else:
            self._logger = logger

    def get_thread(self):
        """Get thread used for running this profiler."""

        return self._thread

    def start(self, subject: ProfiledSubject):
        """Start profiling thread."""

        self._subject = subject
        self._request_stop = False
        self._stopper = threading.Condition()

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

    def run(self):
        """To be overriden by profiler implementation. Most of the time, the
        implementation would do something like:

            while not self.should_stop():
                do_something_useful()
        """

        pass


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

    def mark(self):
        """Call mark() on all underlying profilers."""

        for prof in self._profilers:
            prof.mark()
