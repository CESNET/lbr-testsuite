"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Implementation of profiler reading various Pipeline-specific stats.
"""

import time

import matplotlib.pyplot as plt
import pandas

from .profiler import ProfiledSubject, ProfilerMarker, ThreadedProfiler


class ProfiledPipelineSubject(ProfiledSubject):
    def __init__(self, pipeline):
        super().__init__(pipeline.get_pid())
        self._pipeline = pipeline

    def get_pipeline(self):
        return self._pipeline

    def __repr__(self):
        sys_if = self._pipeline.get_sys_if()
        return f"subject-{self.get_pid()}-{sys_if}"


class PipelineMonProfiler(ThreadedProfiler):
    def __init__(self, csv_file, mark_file, png_file_pattern, time_step=0.1):
        super().__init__()

        self._csv_file = csv_file
        self._mark_file = mark_file
        self._png_file_pattern = png_file_pattern
        self._time_step = time_step

    def start(self, subject: ProfiledSubject):
        if not isinstance(subject, ProfiledPipelineSubject):
            raise RuntimeError("subject must be of type ProfiledPipelineSubject")

        self._marker = ProfilerMarker()
        super().start(subject)

    def _make_timestamps_relative(self, timestamps, lowest=None):
        if lowest is None:
            lowest = timestamps.min()

        return timestamps.sub(lowest).add(1).round(2).astype("float")

    def _plot_to_file(self, plot, png_file, legend=True):
        if legend:
            plot.legend(fontsize=8, bbox_to_anchor=(1, 1), ncol=2)
        f = plot.get_figure()
        f.set_layout_engine("tight")
        self._logger.info(f"save PNG file: {png_file}")
        plot.get_figure().savefig(png_file)

    def _plot_latencies(self, df, ax, label="latencies", column="latency"):
        return df.plot(
            title=f"Pipeline {label}",
            xlabel="time [s]",
            ylabel="latency [us]",
            kind="line",
            style=".-",
            x="timestamp",
            y=filter(lambda k: k.startswith(f"{column}_"), df.columns),
            figsize=(len(df["timestamp"]) * 0.2, 30),
            legend=False,
            ax=ax,
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

    def _plot_general(self, df):
        df = df.copy()
        lowest = df["timestamp"].min()
        df["timestamp"] = self._make_timestamps_relative(df["timestamp"], lowest=lowest)

        fig, axes = plt.subplots(nrows=5, ncols=1)

        self._plot_latencies(df, axes[0])
        self._plot_latencies(df, axes[1], label="maximal latencies", column="max_latency")

        self._plot_chain_calls(df, axes[2])
        self._plot_seen_pkts(df, axes[3])
        self._plot_drop_pkts(df, axes[4])

        self._draw_marks(axes, lowest)

        png_file = str(self._png_file_pattern).format("general")
        self._plot_to_file(fig, png_file)

    def _plot_stage_latencies(self, df, proc_names):
        png_file = str(self._png_file_pattern).format("stage_latencies")

        lowest = df["timestamp"].min()
        df["timestamp"] = self._make_timestamps_relative(df["timestamp"], lowest=lowest)
        df = df.filter(
            items=filter(
                lambda k: k.startswith("stage_cur_latency") or k == "timestamp",
                df.columns,
            )
        )
        df = df.rename(columns=lambda name: name.replace("stage_cur_latency_", ""))
        fig, axes = plt.subplots(nrows=len(proc_names), ncols=1, sharey=True)

        for name, ax in zip(proc_names, axes):
            df.plot(
                title=f"Stage {name} latency",
                xlabel="time [s]",
                ylabel=f"{name} latency [us]",
                kind="line",
                style=".-",
                x="timestamp",
                y=filter(lambda k: k.startswith(name), df.columns),
                figsize=(len(df["timestamp"]) * 0.2, 30),
                legend=False,
                ax=ax,
            )

        self._draw_marks(axes, lowest)

        self._plot_to_file(fig, png_file)

    def _plot_cumulative_data(self, df, ax, label, column):
        df = df.copy()

        for name in df.columns:
            if name.startswith(f"{column}_"):
                df[name] = df[name].diff()

        return df.plot(
            title=f"Pipeline {label}",
            xlabel="time [s]",
            ylabel=f"{label}",
            kind="line",
            style=".-",
            x="timestamp",
            y=filter(lambda k: k.startswith(f"{column}_"), df.columns),
            figsize=(len(df["timestamp"]) * 0.2, 30),
            legend=False,
            ax=ax,
        )

    def _plot_chain_calls(self, df, ax):
        return self._plot_cumulative_data(df, ax, label="chain calls", column="chain_calls")

    def _plot_seen_pkts(self, df, ax):
        return self._plot_cumulative_data(df, ax, label="seen packets (volume)", column="seen_pkts")

    def _plot_drop_pkts(self, df, ax):
        return self._plot_cumulative_data(
            df, ax, label="dropped packets (last stage)", column="drop_pkts"
        )

    def mark(self):
        self._marker.mark(time.monotonic())

    def run(self):
        pipeline = self._subject.get_pipeline()
        workers = pipeline.get_workers_count()
        proc_names = pipeline.get_pipeline_stage_names()
        data = {"timestamp": []}

        for i in range(workers):
            data[f"max_latency_{i}"] = []
            data[f"latency_{i}"] = []
            data[f"chain_calls_{i}"] = []
            data[f"seen_pkts_{i}"] = []
            data[f"drop_pkts_{i}"] = []
            for name in proc_names:
                data[f"stage_max_latency_{name}_{i}"] = []
                data[f"stage_cur_latency_{name}_{i}"] = []

        pipeline.wait_until_active()

        while not self.wait_stoppable(self._time_step):
            now = time.monotonic()
            status = []
            chain_status = []

            for i in range(workers):
                status.append(pipeline.get_worker_status(i))
                chain_status.append(pipeline.get_worker_chain_status(i))

            data["timestamp"].append(now)

            for i, s in enumerate(status):
                max_latency, unit = s["max_latency"].split(" ", 2)
                assert unit == "us"

                latency, unit = s["cur_latency"].split(" ", 2)
                assert unit == "us"

                chain_calls = int(s["chain_calls"])
                seen_pkts = int(s["seen_pkts"])
                drop_pkts = int(s["drop_pkts"])

                data[f"max_latency_{i}"].append(float(max_latency))
                data[f"latency_{i}"].append(float(latency))
                data[f"chain_calls_{i}"].append(chain_calls)
                data[f"seen_pkts_{i}"].append(seen_pkts)
                data[f"drop_pkts_{i}"].append(drop_pkts)

                for j, name in enumerate(proc_names):
                    stage_max, unit = chain_status[i][f"max_latency[{j}]"].split(" ", 2)
                    assert unit == "us"
                    stage_cur, unit = chain_status[i][f"cur_latency[{j}]"].split(" ", 2)
                    assert unit == "us"

                    data[f"stage_max_latency_{name}_{i}"].append(float(stage_max))
                    data[f"stage_cur_latency_{name}_{i}"].append(float(stage_cur))

        self._logger.info(f"sampled {len(data)}x pipeline status")

        df = pandas.DataFrame(data)
        df.to_csv(self._csv_file)

        with open(self._mark_file, "w") as f:
            self._marker.save(f)

        self._plot_general(df)
        self._plot_stage_latencies(df, proc_names)
