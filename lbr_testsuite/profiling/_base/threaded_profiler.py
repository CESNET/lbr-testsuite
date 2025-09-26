"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Supporting code for implementing application profilers.
"""

import logging
import pickle
import threading
from pathlib import Path

import pandas

from .concurrent_profiler import CollectedData
from .profiler import ProfiledSubject, Profiler, ProfilerMarker


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

    def _data_restore(self) -> CollectedData:
        df = None
        data = tuple()
        if Path(self._reserved_files["csv"]).is_file():
            df = pandas.read_csv(self._reserved_files["csv"])

        if Path(self._reserved_files["raw"]).is_file():
            with open(self._reserved_files["raw"], "rb") as in_f:
                data = pickle.load(in_f)

        if Path(self._reserved_files["mark"]).is_file():
            with open(self._reserved_files["mark"], "r") as in_f:
                self._marker = ProfilerMarker.load(in_f)

        if df is None and not data:
            raise RuntimeError("No data files to restore.")

        if df is not None:
            return (df,) + data
        else:
            return data

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

    def postprocess_stored_data(self):
        data = self._data_restore()

        self._data_postprocess(*data)
