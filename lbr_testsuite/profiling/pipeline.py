"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Implementation of profiler reading various Pipeline-specific stats.
"""

import time

import pandas

from . import _charts as charts
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


class PipelineMonContext:
    """Context for monitoring a single pipeline from data provided by PipelineRuntime."""

    def __init__(self, runtime, name=None):
        self._name = name
        self._workers = runtime.get_workers_count(name=self._name)
        self._stages = runtime.get_pipeline_stage_names(name=self._name)
        self._data = {"timestamp": []}
        self._runtime = runtime

        for i in range(self._workers):
            self._data[f"max_latency_{i}"] = []
            self._data[f"latency_{i}"] = []
            self._data[f"chain_calls_{i}"] = []
            self._data[f"seen_pkts_{i}"] = []
            self._data[f"drop_pkts_{i}"] = []
            for name in self._stages:
                self._data[f"stage_max_latency_{name}_{i}"] = []
                self._data[f"stage_cur_latency_{name}_{i}"] = []

    def get_stages(self):
        """Get stage names of the contextual pipeline.

        Returns
        -------
        list[str]
            List of stage names.
        """

        return self._stages

    def sample(self, now=None):
        """Sample data from the contextual pipeline.

        The stored samples are organized into columns, every single sample is
        a single line:

        - timestamp - monotonic timestamp of each row
        - cur_latency_{W} - immediate latency of whole pipeline (per worker)
        - max_latency_{W} - maximal latency of whole pipeline in the last period
        - chain_calls_{W} - number of pipeline chain calls so far
        - seen_pkts_{W} - number of packets seen by the pipeline so for
        - drop_pkts_{W} - number of dropped packets by the pipeline so far
        - stage_cur_latency_{stage}_{W} - immediate latency of a particular pipeline stage
        - stage_max_latency_{stage}_{W} - max latency of a particular pipeline stage

        Parameters
        ----------
        now : time, optional
            Time point of the sample (would be time.monotonic() if not given).
        """

        if now is None:
            now = time.monotonic()

        status = []
        chain_status = []

        for i in range(self._workers):
            status.append(self._runtime.get_worker_status(i, name=self._name))
            chain_status.append(self._runtime.get_worker_chain_status(i, name=self._name))

        self._data["timestamp"].append(now)

        for i, s in enumerate(status):
            max_latency, unit = s["max_latency"].split(" ", 2)
            assert unit == "us"

            latency, unit = s["cur_latency"].split(" ", 2)
            assert unit == "us"

            chain_calls = int(s["chain_calls"])
            seen_pkts = int(s["seen_pkts"])
            drop_pkts = int(s["drop_pkts"])

            self._data[f"max_latency_{i}"].append(float(max_latency))
            self._data[f"latency_{i}"].append(float(latency))
            self._data[f"chain_calls_{i}"].append(chain_calls)
            self._data[f"seen_pkts_{i}"].append(seen_pkts)
            self._data[f"drop_pkts_{i}"].append(drop_pkts)

            for j, name in enumerate(self._stages):
                stage_max, unit = chain_status[i][f"max_latency[{j}]"].split(" ", 2)
                assert unit == "us"
                stage_cur, unit = chain_status[i][f"cur_latency[{j}]"].split(" ", 2)
                assert unit == "us"

                self._data[f"stage_max_latency_{name}_{i}"].append(float(stage_max))
                self._data[f"stage_cur_latency_{name}_{i}"].append(float(stage_cur))

    def get_samples(self):
        """Obtain all stored samples.

        Returns
        -------
        dict
            Dictionary of data samples for each worker of the contextual pipeline.
        """

        return self._data

    def get_data_frame(self):
        """Obtain pandas data frame representing the samples.

        Returns
        -------
        pandas.DataFrame
            Stored samples converted into DataFrame.
        """

        return pandas.DataFrame(self._data)


class PipelineMonProfiler(ThreadedProfiler):
    def __init__(self, csv_file, mark_file, charts_file_pattern, time_step=0.1):
        super().__init__()

        self._csv_file = csv_file
        self._mark_file = mark_file
        self._charts_file_pattern = charts_file_pattern
        self._time_step = time_step

    def start(self, subject: ProfiledSubject):
        if not isinstance(subject, ProfiledPipelineSubject):
            raise RuntimeError("subject must be of type ProfiledPipelineSubject")

        self._marker = ProfilerMarker()
        super().start(subject)

    @staticmethod
    def _compose_ch_spec(df, kind, y_label, col_prefix):
        return charts.SubPlotSpec(
            title=f"Pipeline {kind}",
            y_label=y_label,
            columns=[c for c in df.columns if c.startswith(f"{col_prefix}_")],
        )

    def _plot_general(self, df, markers):
        df = df.copy()

        ch_spec = []
        ch_spec.append(self._compose_ch_spec(df, "latencies", "latency [us]", "latency"))
        ch_spec.append(
            self._compose_ch_spec(df, "maximal latencies", "latency [us]", "max_latency")
        )
        for label, col_prefix in (
            ("chain calls", "chain_calls"),
            ("seen packets (volume)", "seen_pkts"),
            ("dropped packets (last stage)", "drop_pkts"),
        ):
            for c in df.columns:
                if c.startswith(f"{col_prefix}_"):
                    df[c] = df[c].diff()
            ch_spec.append(self._compose_ch_spec(df, label, label, col_prefix))

        charts_file = str(self._charts_file_pattern).format("general")
        charts.create_charts_html(
            df,
            ch_spec,
            charts_file,
            title="Pipeline Statistics",
            markers=list(markers),
        )

    def _plot_stage_latencies(self, df, proc_names, markers):
        df = df.copy()

        df = df.filter(
            items=filter(
                lambda k: k.startswith("stage_cur_latency") or k == "timestamp",
                df.columns,
            )
        )
        df = df.rename(columns=lambda name: name.replace("stage_cur_latency_", ""))

        ch_spec = []
        for name in proc_names:
            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"Stage {name} latency",
                    y_label=f"{name} latency [us]",
                    columns=[c for c in df.columns if c.startswith(f"{name}_")],
                )
            )

        charts_file = str(self._charts_file_pattern).format("stage_latencies")
        charts.create_charts_html(
            df,
            ch_spec,
            charts_file,
            title="Pipeline Statistics",
            markers=list(markers),
        )

    def mark(self):
        self._marker.mark(time.monotonic())

    def run(self):
        pipeline = self._subject.get_pipeline()
        context = PipelineMonContext(pipeline)

        pipeline.wait_until_active()

        while not self.wait_stoppable(self._time_step):
            now = time.monotonic()
            context.sample(now)

        self._logger.info(f"sampled {len(context.get_samples())}x pipeline status")

        df = context.get_data_frame()
        df.to_csv(self._csv_file)

        with open(self._mark_file, "w") as f:
            self._marker.save(f)

        df["timestamp"] = self._make_timestamps_relative(df["timestamp"])
        markers = self._make_timestamps_relative(pandas.Series([m for m in self._marker]))
        self._plot_general(df, markers)
        self._plot_stage_latencies(df, context.get_stages(), markers)
