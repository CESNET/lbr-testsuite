"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Implementation of profiler measuring CPU frequencies.
"""

import logging
import time
from collections import defaultdict

import pandas
import psutil

from . import _charts as charts
from .profiler import ThreadedProfiler


global_logger = logging.getLogger(__name__)


class CPUMonProfiler(ThreadedProfiler):
    """Profiler that is running a thread that continuously collects data
    about CPU frequencies. It plots two charts:

    * count of CPUs in time at certain frequency levels
    * relative time spent at certain frequency level for each CPU during measurement

    Frequency measurements are stored in CSV file named _raw_ in their original form.
    The particular outputs then consist of a CSV file and charts file, here
    the frequencies are rounded to hundred MHz (the original precision is not useful).
    """

    def __init__(self, csv_file_pattern, charts_file_pattern, time_step=0.1):
        super().__init__()

        self._csv_file_pattern = csv_file_pattern
        self._charts_file_pattern = charts_file_pattern
        self._time_step = time_step

    def _cpu_names(self):
        names = []

        for i in range(len(psutil.cpu_freq(True))):
            names.append(f"cpu_{i}")

        return names

    def _round_freq(self, freq):
        return round(freq / 100) * 100

    def _collect_cpu_freq_columns(self, df):
        return list(filter(lambda name: name.startswith("cpu_"), df.columns))

    def _collect_freqs(self, df, cpus):
        all_freqs = set()

        for i in range(len(df)):
            for cpu in cpus:
                all_freqs.add(self._round_freq(df.iloc[i].loc[cpu]))

        return all_freqs

    def _data_to_df(self, data, csv_file):
        df = pandas.DataFrame(data)
        global_logger.info(f"save CSV file: {csv_file}")
        df.to_csv(csv_file)

        return df

    def _plot_freqs_per_cpu(self, df, csv_file, charts_file):
        cpus = self._collect_cpu_freq_columns(df)
        all_freqs = self._collect_freqs(df, cpus)
        data = defaultdict(list)

        for cpu in cpus:
            freq_hist = {}

            for freq in all_freqs:
                freq_hist[freq] = 0

            for i in range(len(df)):
                freq_hist[self._round_freq(df.iloc[i].loc[cpu])] += 1

            data["cpu"].append(cpu)

            freq_total = sum(freq_hist.values())
            for freq, count in freq_hist.items():
                data[freq].append(100 * count / freq_total)

        df = self._data_to_df(data, csv_file)

        all_cols = list(df.keys())
        all_cols.remove("cpu")
        chart_spec = charts.SubPlotSpec(
            title="CPU frequencies",
            x_col="cpu",
            x_label="CPU",
            y_label="Time at frequency level (%)",
            columns=all_cols,
            chart_type=charts.ChartType.BAR,
        )

        charts.create_charts_html(
            df,
            chart_spec,
            charts_file,
            title="CPU Frequencies",
            barmode="stack",
        )

    def _make_freqs_hist(self, df, cpus, row):
        hist = {}

        for freq in self._collect_freqs(df, cpus):
            hist[freq] = 0

        for cpu in cpus:
            hist[self._round_freq(df.iloc[row].loc[cpu])] += 1

        return hist

    def _plot_freqs(self, df, csv_file, charts_file):
        cpus = self._collect_cpu_freq_columns(df)
        data = defaultdict(list)

        for i in range(len(df)):
            data["timestamp"].append(df.iloc[i].loc["timestamp"])

            for freq, count in self._make_freqs_hist(df, cpus, i).items():
                data[freq].append(count)

        df = self._data_to_df(data, csv_file)

        all_cols = list(df.keys())
        all_cols.remove("timestamp")
        chart_spec = charts.SubPlotSpec(
            title="CPU frequencies in time (MHz)",
            y_label=f"CPU count (out of {len(cpus)} CPUs)",
            columns=all_cols,
            y_ticks=list(range(0, len(cpus) + 1, 3)),
        )

        charts.create_charts_html(df, chart_spec, charts_file, title="CPU Frequencies")

    def run(self):
        cpu_names = self._cpu_names()
        data = {"timestamp": []}

        for name in cpu_names:
            data[name] = []

        while not self.wait_stoppable(self._time_step):
            now = time.monotonic()
            data["timestamp"].append(now)

            for i, freq in enumerate(psutil.cpu_freq(True)):
                data[f"cpu_{i}"].append(freq.current)

        df = pandas.DataFrame(data)
        df.to_csv(str(self._csv_file_pattern).format("raw"))

        df["timestamp"] = self._make_timestamps_relative(df["timestamp"])
        self._plot_freqs_per_cpu(
            df,
            str(self._csv_file_pattern).format("freqs_per_cpu"),
            str(self._charts_file_pattern).format("freqs_per_cpu"),
        )
        self._plot_freqs(
            df,
            str(self._csv_file_pattern).format("freqs"),
            str(self._charts_file_pattern).format("freqs"),
        )
