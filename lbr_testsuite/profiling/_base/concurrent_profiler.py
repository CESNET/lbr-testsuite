"""
Author(s):
    Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Supporting code for implementing various profilers which should run
concurrently.
"""

import logging
import pickle
import string
from pathlib import Path
from typing import TypeAlias

import pandas

from .concurrent_engine import ConcurrentEngine
from .process_engine import ProcessEngine
from .profiler import ProfiledSubject, Profiler, ProfilerMarker


CollectedData: TypeAlias = tuple[pandas.DataFrame, any] | tuple[any]


class ConcurrentProfiler(Profiler):
    """Abstract class that implements common profiler logic
    that runs as a Python code concurrently (i.e. in separate processes
    or threads).
    """

    def __init__(
        self,
        logger: logging.Logger = None,
        output_file_base: str = "./",
        concurrent_engine_cls: type[ConcurrentEngine] = ProcessEngine,
    ):
        """
        Parameters
        ----------
        logger: logging.Logger, optional
            A logging facility.
        output_file_base: str, optional
            Base file name for all output files. This base file name
            is a template, used for composition of various file names.
            Use `custom_file` or `charts_file` methods to compose
            output file names.
        concurrent_engine_cls: type[ConcurrentEngine], optional
            Engine providing API for execution of concurrent profilers.
        """

        if logger is None:
            self._logger = logging.getLogger(type(self).__name__)
        else:
            self._logger = logger

        self._engine = concurrent_engine_cls()

        self._output_file_base = output_file_base
        self._reserved_files = dict(
            csv=f"{self._format_file_name(output_file_base)}_raw.csv",
            raw=f"{self._format_file_name(output_file_base)}_raw",
            mark=f"{self._format_file_name(output_file_base)}_raw.mark",
        )
        self._marker = None

    @staticmethod
    def _check_template(template):
        """Check that the template contains only positional replacement
        fields with sequential order starting from zero.

        Only such template is easily usable with arguments expansion
        using `*args` syntax.

        Parameters
        ----------
        template: str
            Template to check.

        Returns
        -------
        int
            Count of replacement fields.

        Valid examples:

        template = "Example"
        template2 = "Example {0} {1} {2}"

        Invalid examples:

        template3 = "Example {0} {1} {5}"
        template4 = "Example {whatever}"

        """

        formatter = string.Formatter()
        fields = [fname for _, fname, _, _ in formatter.parse(template) if fname is not None]
        assert [int(f) for f in fields] == list(range(len(fields))), "An invalid template"

        return len(fields)

    @staticmethod
    def _format_file_name(file_name_base, *args):
        """Format a file_name_base template with (optional) arguments.

        The template may contain up to 100 replacement fields. However,
        this number is intentionally huge. It is not expected to use
        more than few replacement fields. If there are not enough
        arguments in `*args` for all replacement fields in the template
        default empty string is used.
        """

        default_str = ""

        r_fields_cnt = ConcurrentProfiler._check_template(str(file_name_base))
        not_provided_cnt = r_fields_cnt - len(args)
        default_args = not_provided_cnt * (default_str,)

        return str(file_name_base).format(*(args + default_args))

    def custom_file(self, suffix, *args):
        """Compose file name of a custom file.

        Parameters
        ----------
        suffix: str
            File suffix.
        *args:
            List of arguments, which will be filled in self._output_file_base
            template.
        """

        fn = f"{self._format_file_name(self._output_file_base, *args)}.{suffix}"
        assert (
            fn not in self._reserved_files.values()
        ), "Requested custom file may overwrite a reserved file"

        return fn

    def charts_file(self, *args):
        """Compose charts file name.

        Parameters
        ----------
        suffix: str
            File suffix.
        *args:
            List of arguments, which will be filled in self._output_file_base
            template.
        """

        return self.custom_file("html", *args)

    def start(self, subject: ProfiledSubject):
        """Start the profiler."""

        self._subject = subject
        self._marker = ProfilerMarker()

        self._engine.start(self._run, repr(self._subject))

    def wait_stoppable(self, timeout: float) -> bool:
        """Method can be used to stop execution of the current profiler
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

        return self._engine.wait_stoppable(timeout)

    def get_name(self) -> str:
        """Get name of the underlying process object."""

        return self._engine.get_name()

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

    def _run(self):
        data = self._data_collect()
        if not isinstance(data, tuple):
            data = (data,)

        self._data_store(data)

        self._data_postprocess(*data)

    def postprocess_stored_data(self):
        """Post-process measured data

        Post-processing might be done independently on measurement.
        Source data are always read from predefined files, no matter
        if they are from current or some former measurement.
        """

        data = self._data_restore()

        self._data_postprocess(*data)

    def stop(self):
        """Stop the profiler."""

        self._engine.stop()

    def join(self):
        """Wait for the profiler to finish."""

        self._engine.join()
