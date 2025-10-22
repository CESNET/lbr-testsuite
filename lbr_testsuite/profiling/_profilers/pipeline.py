"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Implementation of profiler reading various Pipeline-specific stats.
"""

import time

import pandas

from .._base import charts
from .._base.profiler import ProfiledSubject
from .._base.threaded_profiler import ThreadedProfiler


class ProfiledPipelineSubject(ProfiledSubject):
    def __init__(self, pipeline):
        super().__init__(pipeline.get_pid())
        self._pipeline = pipeline
        # store sys interface for usage in __repr__ so the method will not fail
        # even when pipeline is not ready
        self._repr_sys_if = pipeline.get_sys_if()

    def get_pipeline(self):
        return self._pipeline

    def __repr__(self):
        return f"subject-{self.get_pid()}-{self._repr_sys_if}"


class PipelineMonContext:
    """Context for monitoring a single pipeline from data provided by PipelineRuntime."""

    def __init__(self, runtime, name=None):
        self._name = name
        self._workers = runtime.get_workers_count(name=self._name)
        self._stages = list(runtime.get_pipeline_stage_names(name=self._name))
        self._data = {"timestamp": []}
        self._runtime = runtime

        for i in range(self._workers):
            s = runtime.get_worker_status(i, name=self._name)
            ids = f"{s['lcore_id']}(phy{s['cpu_id']})"

            self._data[f"max_latency_{ids}"] = []
            self._data[f"latency_{ids}"] = []
            self._data[f"chain_calls_{ids}"] = []
            self._data[f"nombuf_calls_{ids}"] = []
            self._data[f"seen_pkts_{ids}"] = []
            self._data[f"drop_pkts_{ids}"] = []
            for name in self._stages:
                self._data[f"stage_max_latency_{name}_{ids}"] = []
                self._data[f"stage_cur_latency_{name}_{ids}"] = []

    def terminate(self):
        """Terminate data collection and prepare context for storage."""

        self._runtime = None

    def get_name(self):
        """Get name of this pipeline.

        Returns
        -------
        str
            Name of pipeline.
        """

        return self._name

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
            nombuf_calls = int(s["nombuf_calls"])
            seen_pkts = int(s["seen_pkts"])
            drop_pkts = int(s["drop_pkts"])

            ids = f"{s['lcore_id']}(phy{s['cpu_id']})"
            self._data[f"max_latency_{ids}"].append(float(max_latency))
            self._data[f"latency_{ids}"].append(float(latency))
            self._data[f"chain_calls_{ids}"].append(chain_calls)
            self._data[f"nombuf_calls_{ids}"].append(nombuf_calls)
            self._data[f"seen_pkts_{ids}"].append(seen_pkts)
            self._data[f"drop_pkts_{ids}"].append(drop_pkts)

            for j, name in enumerate(self._stages):
                stage_max, unit = chain_status[i][f"max_latency[{j}]"].split(" ", 2)
                assert unit == "us"
                stage_cur, unit = chain_status[i][f"cur_latency[{j}]"].split(" ", 2)
                assert unit == "us"

                self._data[f"stage_max_latency_{name}_{ids}"].append(float(stage_max))
                self._data[f"stage_cur_latency_{name}_{ids}"].append(float(stage_cur))

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
    def __init__(self, time_step=0.1, **kwargs):
        super().__init__(**kwargs)

        self._time_step = time_step

    def start(self, subject: ProfiledSubject):
        if not isinstance(subject, ProfiledPipelineSubject):
            raise RuntimeError("subject must be of type ProfiledPipelineSubject")
        super().start(subject)

    @staticmethod
    def _compose_ch_spec(df, kind, y_label, col_prefix):
        return charts.SubPlotSpec(
            title=f"Pipeline {kind}",
            y_label=y_label,
            columns=[c for c in df.columns if c.startswith(f"{col_prefix}_")],
        )

    def _plot_general(self, pipeline_name, df, markers):
        df = df.copy()

        df["timestamp_diff"] = df["timestamp"].diff()

        ch_spec = []
        ch_spec.append(self._compose_ch_spec(df, "latencies", "latency [us]", "latency"))
        ch_spec.append(
            self._compose_ch_spec(df, "maximal latencies", "latency [us]", "max_latency")
        )
        for label, col_prefix in (
            ("chain calls", "chain_calls"),
            ("empty-burst calls", "nombuf_calls"),
            ("seen packets (volume)", "seen_pkts"),
            ("dropped packets (last stage)", "drop_pkts"),
        ):
            for c in df.columns:
                if c.startswith(f"{col_prefix}_"):
                    df[c] = df[c].diff().div(df["timestamp_diff"] / self._time_step)
            ch_spec.append(self._compose_ch_spec(df, label, label, col_prefix))

        charts.create_charts_html(
            df,
            ch_spec,
            self.charts_file(f"_general_{pipeline_name}"),
            title="Pipeline Statistics",
            markers=markers,
        )

    def _plot_stage_latencies(self, pipeline_name, df, proc_names, markers):
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

        charts.create_charts_html(
            df,
            ch_spec,
            self.charts_file(f"_stage_latencies_{pipeline_name}"),
            title="Pipeline Statistics",
            markers=markers,
        )

    def mark(self, desc=None):
        self._marker.mark(time.monotonic(), desc)

    def _data_collect(self) -> list[PipelineMonContext]:
        pipeline = self._subject.get_pipeline()
        names = pipeline.get_pipeline_names()
        contexts = [PipelineMonContext(pipeline, name) for name in names]

        pipeline.wait_until_active()

        while not self.wait_stoppable(self._time_step):
            now = time.monotonic()

            for ctx in contexts:
                ctx.sample(now)

        self._logger.info(f"sampled {len(contexts[0].get_samples())}x pipeline status")

        for ctx in contexts:
            ctx.terminate()
        return contexts

    def _data_postprocess(self, data: list[PipelineMonContext]):
        for ctx in data:
            df = ctx.get_data_frame()
            df.to_csv(self.custom_file("csv", f"_{ctx.get_name()}"))

            markers = self._marker.to_dataframe()
            markers["time"] = self._make_timestamps_relative(markers["time"], df["timestamp"].min())
            df["timestamp"] = self._make_timestamps_relative(df["timestamp"])
            self._plot_general(ctx.get_name(), df, markers)
            self._plot_stage_latencies(ctx.get_name(), df, ctx.get_stages(), markers)
