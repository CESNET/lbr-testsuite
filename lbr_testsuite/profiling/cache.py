"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Implementation of profiler for measuring per-process data.
"""

import os
import time
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Dict, List, NamedTuple

import matplotlib.pyplot as plt
import pandas
from pypapi import papi_low as papi
from pypapi.exceptions import PapiNoEventError

from .profiler import ProfilerMarker, ThreadedProfiler


class ThreadInfo(NamedTuple):
    """Utility class for storing thread information."""

    id: int
    name: str


def find_dpdk_worker_threads(pid: int) -> List[ThreadInfo]:
    """Utility function used to lookup threads managed by given pid and
    filter threads whose names start with `dpdk-worker`.

    Parameters
    ----------
    pid : int
        PID of the process whose threads to look up.

    Returns
    -------
    List[ThreadInfo]
        List of thread informations corresponding to individual
        DPDK worker threads.
    """

    ret = []
    for thread_dir in Path(f"/proc/{pid}/task").iterdir():
        tid = int(thread_dir.name)
        name = (thread_dir / "comm").read_text().strip()

        if name.startswith("dpdk-worker"):
            ret.append(ThreadInfo(tid, name))

    return ret


class PapiThreadContext:
    """Class wrapping the PAPI eventset providing methods
    to start, stop and sample the PAPI counters."""

    def __init__(
        self,
        eventset: int,
        event_list: List[int],
        thread: ThreadInfo,
    ):
        """
        Parameters
        ----------
        eventset : int
            Integer handle to the underlying PAPI eventset.
        event_list : List[int]
            List of events managed by the eventset.
        thread : ThreadInfo
            Thread to which the eventset belongs.
        """

        self._eventset = eventset
        self._event_list = event_list
        self._thread = thread

    def start(self):
        """Start measuring PAPI counters of underlying eventset."""

        papi.start(self._eventset)

    def sample(self) -> Dict[str, int]:
        """Sample counters of the underlying eventset.

        Returns
        -------
        Dict[str, int]
            Dictionary with thread names and counter names as keys
            and the counter values as values.
        """

        zero_samples = [0 for _ in self._event_list]
        samples = papi.accum(self._eventset, zero_samples)

        return {
            f"{self._thread.name}_{papi.event_code_to_name(cnt)}": value
            for cnt, value in zip(self._event_list, samples)
        }

    def stop(self):
        """Stop measuring PAPI counters of underlying eventset."""

        papi.stop(self._eventset)


class PapiMultiThreadContext:
    """Wrapper over multiple PapiThreadContext for measuring
    more threads at once."""

    def __init__(self, contexts: List[PapiThreadContext]):
        """
        Parameters
        ----------
        contexts : List[PapiThreadContext]
            Managed list of PapiThreadContext objects.
        """

        self._contexts = contexts

    def start(self):
        """Start measurement of all underlying contexts."""

        for c in self._contexts:
            c.start()

    def sample(self) -> Dict[str, int]:
        """Sample the PAPI counters of all underlying contexts and
        compose them into a single dictionary.

        Returns
        -------
        Dict[str, int]
            Dictionary with thread names and counter names as keys
            and the counter values as values.
        """

        ret = {}
        for c in self._contexts:
            s = c.sample()
            ret = {**ret, **s}

        return ret

    def stop(self):
        """Stop the measurement of all underlying contexts."""

        for c in self._contexts:
            c.stop()


@contextmanager
def papi_context_manager(event_list: List[int], thread: ThreadInfo):
    """Context manager used to manage an instance of PapiThreadContext
    for a given thread.

    Parameters
    ----------
    event_list : List[int]
        List of events to be measured.
    thread : ThreadInfo
        Object representing the thread which is measured.

    Returns
    -------
    PapiThreadContext
        Managed instance of context for given thread.
    """

    eventset = papi.create_eventset()
    papi.assign_eventset_component(eventset, 0)  # << By convention, 0 is always the cpu component.

    for ev in event_list:
        papi.add_event(eventset, ev)

    papi.attach(eventset, thread.id)

    yield PapiThreadContext(eventset, event_list, thread)

    papi.detach(eventset)
    papi.cleanup_eventset(eventset)
    papi.destroy_eventset(eventset)


@contextmanager
def papi_multi_context_manager(event_list: List[int], threads: List[ThreadInfo]):
    """Context manager managing multiple contexts within a single PapiMultiThreadContext.

    Parameters
    ----------
    event_list : List[int]
        List of PAPI events to be measured.
    threads : List[ThreadInfo]
        List of threads to be measured.

    Returns
    -------
    PapiMultiThreadContext
        Wrapper object over multiple PapiThreadContext for multi threaded measurement.
    """

    # ExitStack object can be used to manage multiple context manager as one.
    # By calling 'enter_context()' the provided context manager is entered and stored
    # within the ExitStack object. At the end of the 'with' block, the stack object
    # is destroyed together with all underlying context managers.
    # See https://docs.python.org/3/library/contextlib.html#contextlib.ExitStack
    with ExitStack() as stack:
        contexts = [stack.enter_context(papi_context_manager(event_list, t)) for t in threads]
        yield PapiMultiThreadContext(contexts)


class PAPIProfiler(ThreadedProfiler):
    """Profiler for cache events using PAPI events."""

    def __init__(
        self,
        csv_file: Path,
        mark_file: str,
        png_file: str,
        event_groups: Dict[str, List],
        time_step: float = 0.1,
    ):
        """
        Parameters
        ----------
        csv_file : Path
            Path to the output csv file.
        png_file_pattern : str
            Base of the png file name.
        event_groups : Dict[str, List]
            Event groups dictionary in the format:
                {"name": list of events in group}
        time_step : float
            Time step between two consecutive measurements.
        """

        super().__init__()

        self._csv_file = csv_file
        self._mark_file = mark_file
        self._png_file = png_file
        self._time_step = time_step

        papi_ver = int(os.environ.get("PYPAPI_VER", 0x7010000))

        if papi.is_initialized() == 0:
            papi.library_init(papi_ver)

        self._event_groups = event_groups
        event_list = list({ev for evlist in event_groups.values() for ev in evlist})
        self._event_list = self._filter_supported_events(event_list)

    def _filter_supported_events(self, event_list: List[int]) -> List[int]:
        ret = []
        for ev in event_list:
            try:
                papi.query_event(ev)
            except PapiNoEventError:
                self._logger.warning(f"Event {papi.event_code_to_name(ev)} not found, skipping...")
                continue

            ret.append(ev)

        return ret

    @staticmethod
    def _make_timestamps_relative(timestamps, lowest=None):
        if lowest is None:
            lowest = timestamps.min()

        return timestamps.sub(lowest).add(1).round(2).astype("float")

    def _filter_subframe(self, df: pandas.DataFrame, events: List[int]) -> pandas.DataFrame:
        def is_event(val: str, events: List[int]) -> bool:
            for ev in events:
                if papi.event_code_to_name(ev) in val:
                    return True
            else:
                return False

        return df.filter(
            items=filter(
                lambda k: is_event(k, events) or k == "timestamp",
                df.columns,
            )
        )

    def _draw_marks(self, axes, time_lowest):
        for mark_time in self._marker:
            time = float(round(mark_time - time_lowest + 1, 2))

            self._logger.debug(f"mark at {time}s")

            for ax in axes:
                ax.axvline(
                    x=time,
                    color="b",
                    gapcolor="r",
                    linestyle="--",
                    alpha=0.3,
                    label=f"mark: {time}s",
                )

    def _plot_events_cumulative(
        self,
        df: pandas.DataFrame,
    ):
        lowest = df["timestamp"].min()
        df["timestamp"] = self._make_timestamps_relative(df["timestamp"], lowest=lowest)

        fig, axes = plt.subplots(nrows=len(self._event_groups), ncols=1, sharex=True)

        for group, ax in zip(self._event_groups.keys(), axes):
            df_local = self._filter_subframe(df, self._event_groups[group])
            df_local.plot(
                title=f"PAPI events: {group}",
                xlabel="time [s]",
                ylabel="event count",
                kind="line",
                style=".-",
                x="timestamp",
                figsize=(len(df["timestamp"]) * 0.2, 15),
                legend=True,
                ax=ax,
            )

        self._draw_marks(axes, lowest)

        fig.set_layout_engine("tight")
        self._logger.info(f"saving PNG file: {self._png_file}")
        fig.savefig(self._png_file)

    def start(self, subject):
        self._marker = ProfilerMarker()
        super().start(subject)

    def mark(self):
        self._marker.mark(time.monotonic())

    def run(self):
        pid = self._subject.get_pid()
        workers = find_dpdk_worker_threads(pid)
        data = defaultdict(list)

        with papi_multi_context_manager(self._event_list, workers) as c:
            c.start()

            while not self.wait_stoppable(self._time_step):
                now = time.monotonic()
                data["timestamp"].append(now)

                samples = c.sample()
                for s_name, s_value in samples.items():
                    data[s_name].append(s_value)

            c.stop()

        self._logger.info(f"sampled {len(data)}x cache status")

        df = pandas.DataFrame(data)
        df.to_csv(self._csv_file)

        with open(self._mark_file, "w") as f:
            self._marker.save(f)

        self._plot_events_cumulative(df)