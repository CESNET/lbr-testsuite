"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Implementation of profiler reading various Pipeline-specific stats.
"""

import time

import pandas

from .._base import charts
from .._base.concurrent_profiler import ConcurrentProfiler
from .._base.profiler import ProfiledSubject


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
        self._replicas = runtime.get_replicas_count(name=self._name)
        self._stages = list(runtime.get_pipeline_stage_names(name=self._name))
        self._data = {"timestamp": []}
        self._runtime = runtime

        # Track workers per replica for stage offset calculation
        self._replica_worker_counts = []

        for replica_id in range(self._replicas):
            workers_count = runtime.get_replica_workers_count(replica_id, name=self._name)
            self._replica_worker_counts.append(workers_count)

            for worker_idx in range(workers_count):
                s = runtime.get_replica_worker_status(replica_id, worker_idx, name=self._name)
                ids = f"r{replica_id}w{worker_idx}_{s['lcore_id']}(phy{s['cpu_id']})"

                self._data[f"max_latency_{ids}"] = []
                self._data[f"latency_{ids}"] = []
                self._data[f"chain_calls_{ids}"] = []
                self._data[f"nombuf_calls_{ids}"] = []
                self._data[f"seen_pkts_{ids}"] = []
                self._data[f"drop_pkts_{ids}"] = []
                for stage_name in self._stages:
                    self._data[f"stage_max_latency_{stage_name}_{ids}"] = []
                    self._data[f"stage_cur_latency_{stage_name}_{ids}"] = []

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

    def _count_stages_in_worker(self, chain_status_entry):
        """Count the number of stages in a worker's chain status.

        Stages are identified by strings like 'max_latency[0]', 'max_latency[1]', etc.
        This method counts how many such entries exist.

        Parameters
        ----------
        chain_status_entry : dict
            Chain status dictionary for a single worker.

        Returns
        -------
        int
            Number of stages handled by this worker.
        """

        stage_count = 0

        while f"max_latency[{stage_count}]" in chain_status_entry:
            stage_count += 1

        return stage_count

    def _collect_worker_statistics(self, worker_status, ids):
        """Collect general worker statistics from worker status.

        Parameters
        ----------
        worker_status : dict
            Worker status dictionary containing latency and packet metrics.
        ids : str
            Worker identifier string (e.g., "r0w0_lcore_id(phy cpu_id)").
        """

        max_latency, unit = worker_status["max_latency"].split(" ", 2)
        assert unit == "us"

        latency, unit = worker_status["cur_latency"].split(" ", 2)
        assert unit == "us"

        chain_calls = int(worker_status["chain_calls"])
        nombuf_calls = int(worker_status["nombuf_calls"])
        seen_pkts = int(worker_status["seen_pkts"])
        drop_pkts = int(worker_status["drop_pkts"])

        self._data[f"max_latency_{ids}"].append(float(max_latency))
        self._data[f"latency_{ids}"].append(float(latency))
        self._data[f"chain_calls_{ids}"].append(chain_calls)
        self._data[f"nombuf_calls_{ids}"].append(nombuf_calls)
        self._data[f"seen_pkts_{ids}"].append(seen_pkts)
        self._data[f"drop_pkts_{ids}"].append(drop_pkts)

    def _collect_stage_latencies(self, chain_status_entry, ids, stage_offset=0):
        """Collect stage latency samples from chain status.

        Parameters
        ----------
        chain_status_entry : dict
            Chain status dictionary for a single worker.
        ids : str
            Worker identifier string (e.g., "r0w0_lcore_id(phy cpu_id)").
        stage_offset : int, optional
            Offset to map local stage indices to global stage names.
            Default is 0 (no offset).

        Returns
        -------
        int
            Number of stages processed from this worker's chain status.
        """

        num_stages = self._count_stages_in_worker(chain_status_entry)

        for local_stage_idx in range(num_stages):
            global_stage_idx = stage_offset + local_stage_idx

            stage_name = self._stages[global_stage_idx]
            max_key = f"max_latency[{local_stage_idx}]"
            cur_key = f"cur_latency[{local_stage_idx}]"

            stage_max, unit = chain_status_entry[max_key].split(" ", 2)
            assert unit == "us"
            stage_cur, unit = chain_status_entry[cur_key].split(" ", 2)
            assert unit == "us"

            self._data[f"stage_max_latency_{stage_name}_{ids}"].append(float(stage_max))
            self._data[f"stage_cur_latency_{stage_name}_{ids}"].append(float(stage_cur))

        return num_stages

    def sample(self, now=None):
        """Sample data from the contextual pipeline.

        The stored samples are organized into columns, every single sample is
        a single line:

        - timestamp - monotonic timestamp of each row
        - cur_latency_{R}_{W} - immediate latency of whole pipeline (per replica worker)
        - max_latency_{R}_{W} - maximal latency of whole pipeline in the last period
        - chain_calls_{R}_{W} - number of pipeline chain calls so far
        - seen_pkts_{R}_{W} - number of packets seen by the pipeline so for
        - drop_pkts_{R}_{W} - number of dropped packets by the pipeline so far
        - stage_cur_latency_{stage}_{R}_{W} - immediate latency of a particular pipeline stage
        - stage_max_latency_{stage}_{R}_{W} - max latency of a particular pipeline stage

        Parameters
        ----------
        now : time, optional
            Time point of the sample (would be time.monotonic() if not given).
        """

        if now is None:
            now = time.monotonic()

        self._data["timestamp"].append(now)

        for replica_id in range(self._replicas):
            workers_count = self._replica_worker_counts[replica_id]
            stage_offset = 0

            for worker_idx in range(workers_count):
                s = self._runtime.get_replica_worker_status(replica_id, worker_idx, name=self._name)
                chain_status = self._runtime.get_replica_worker_chain_status(
                    replica_id, worker_idx, name=self._name
                )

                ids = f"r{replica_id}w{worker_idx}_{s['lcore_id']}(phy{s['cpu_id']})"
                self._collect_worker_statistics(s, ids)

                num_stages = self._collect_stage_latencies(chain_status, ids, stage_offset)
                stage_offset += num_stages

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


class PipelineMonProfiler(ConcurrentProfiler):
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
