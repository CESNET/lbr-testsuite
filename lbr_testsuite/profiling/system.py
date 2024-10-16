"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Implementation of profiler reading system-wide information.
"""

import re
import time

import pandas

from . import _charts as charts
from .profiler import ThreadedProfiler


class IrqMonProfiler(ThreadedProfiler):
    """Monitor of system interrupts. It samples counters of all interrupts in the system.
    All such statistics are stored into CSV file and interesting parts are plotted into
    charts file. It plots summary timeline of all interrupts in the system, summary of each
    CPU group and timeline of interrupts per group of CPUs.

    Attributes
    ----------
    GROUP_SIZE : int
        Count of CPUs in a group to be plotted.
    """

    GROUP_SIZE = 8

    def __init__(self, csv_file, charts_file, time_step=0.1):
        """
        Parameters
        ----------
        csv_file : str
            Path to CSV file where to store all sampled data.
        charts_file : str
            Path to charts file where to plot the data.
        time_step : float, optional
            Sampling period (seconds).
        """

        super().__init__()

        self._csv_file = csv_file
        self._charts_file = charts_file
        self._time_step = time_step

    def _read_proc_interrupts(self):
        with open("/proc/interrupts", "r") as f:
            return f.readlines()

    def _parse_headline(self, headline):
        """Parse first line of the /proc/interrupts file. It contains column names
        that identifies each particular CPU. Some column names are empty, they are
        ignored.

        Returns
        -------
        list(str)
            Names of CPUs.
        """

        cpus = []

        for index, entry in enumerate(re.split(r"[ \t]+", headline)):
            if len(entry.strip()) == 0:
                continue

            cpus.append((entry.strip(), index))

        return cpus

    def _parse_dataline(self, dataline):
        return re.split(r"[ \t]+", dataline.lstrip())

    def _collect_interrupts(self):
        """Collect interrupts statistics from the /proc/interrupts file. It parses
        the headline to extract CPU names and than collects the interrupt statistics.

        Returns
        -------
        dict
            Dictionary mapping CPU names to the total number of processed interrupts.
        """

        lines = self._read_proc_interrupts()
        assert len(lines) > 0

        cpus = self._parse_headline(lines[0])
        stats = {cpu[0]: 0 for cpu in cpus}

        for line in lines[1:]:
            data = self._parse_dataline(line)

            for cpu, index in cpus:
                if index < len(data):
                    stats[cpu] += int(data[index])

        return stats

    def _compute_stats(self, df, cpus):
        df["sum"] = df[cpus].sum(axis=1)
        df["avg"] = df[cpus].mean(axis=1)
        df["median"] = df[cpus].median(axis=1)
        df["max"] = df[cpus].max(axis=1)

    def _compute_groups_stats(self, df, groups, size, cpus):
        for i in range(groups):
            first = i * size
            last = (i + 1) * size

            df[f"group{i}"] = df[cpus[first:last]].sum(axis=1)

    def run(self):
        """Sample all system interrupts per CPU, write CSV file with sampled data
        and generate plots.
        """

        last = self._collect_interrupts()
        cpus = list(last.keys())
        data = {k: [] for k in cpus + ["timestamp"]}

        while not self.wait_stoppable(self._time_step):
            now = time.monotonic()
            stats = self._collect_interrupts()

            data["timestamp"].append(now)

            for cpu, count in stats.items():
                data[cpu].append(count - last[cpu])

            last = stats

        self._logger.info(f"save interrupt stats into {self._csv_file}")

        df = pandas.DataFrame(data)
        df.to_csv(self._csv_file)

        groups = len(cpus) // self.GROUP_SIZE + (1 if len(cpus) % self.GROUP_SIZE != 0 else 0)

        df["timestamp"] = self._make_timestamps_relative(df["timestamp"])

        self._compute_stats(df, cpus)
        self._compute_groups_stats(df, groups, self.GROUP_SIZE, cpus)

        # plot summary, groups summary and each particular group
        ch_spec = []
        ch_spec.append(
            charts.SubPlotSpec(
                title="System interrupts (summary)",
                y_label="interrupts",
                columns=["sum", "avg", "median", "max"],
            )
        )
        ch_spec.append(
            charts.SubPlotSpec(
                title="System interrupts (CPU groups)",
                y_label="interrupts",
                columns=[f"group{i}" for i in range(groups)],
            )
        )
        for i in range(groups):
            first = i * self.GROUP_SIZE
            last = (i + 1) * self.GROUP_SIZE

            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"System interrupts (group{i}: {first}..{last-1})",
                    y_label="interrupts",
                    columns=cpus[first:last],
                )
            )

        self._logger.info(f"save charts file: {self._charts_file}")
        charts.create_charts_html(
            df,
            ch_spec,
            self._charts_file,
            title="System Interrupts",
            vertical_spacing=0.03,
        )
