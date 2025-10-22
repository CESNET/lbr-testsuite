"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Implementation of profiler monitoring Rx/Tx statistics. The module
consists of four components:
* StatsRequest - a simple dataclass for selection which Rx/Tx statistics
will be monitored,
* RxTxStats - a definition of all supported Rx/Tx statistics counters
(also contains definition of default statistics request),
* ProfiledPipelineWithStatsSubject - profiled subject class
representation, extended by Rx/Tx statistics,
* RxTxMonProfiler - Rx/Tx statistics monitoring profiler class.

To use RxTxMonProfiler, first create an instance of the class. Than,
start the profiler using the `start()` method. Pass an initialized
instance of ProfiledPipelineWithStatsSubject, optionally with custom
statistics request (set of default statistics is monitored otherwise).
When profiling is done, stop the profiler using the `stop()` method and
observe results!
"""

import time
from dataclasses import dataclass
from enum import StrEnum

import pandas

from lbr_testsuite.dpdk_application.pipeline_runtime import PipelineRuntime

from ...common import common
from .._base import charts
from .._base.threaded_profiler import ThreadedProfiler
from .pipeline import ProfiledPipelineSubject


class CounterUnit(StrEnum):
    """Enumeration providing set of supported counter units."""

    PACKETS = "packets"
    BYTES = "bytes"
    OTHER = "other"


@dataclass
class StatsRequest:
    """Statistics request

    Contains name of counters for extended statistics groups. *_per_q
    counters are per-queue counters. Number of counters depends on count
    of queues used. In a request, name of per-queue counters are used
    without a queue ID (e.g. to select rx_q1_packets, rx_q2_packets, ...
    rx_q<N>_packets use just rx_q_packets name).
    """

    xstats: tuple = ()
    xstats_per_q: tuple = ()


@dataclass
class RxTxStatsConf:
    """Rx-Tx statistics container configuration.

    Attributes
    ----------
    xstats : dict
        Dictionary with selected counters from extended statistics. Keys
        are counter names, values are units.
    xstats_per_q : dict
        Dictionary with selected counters from extended statistics for
        for every queue. Keys are general counter names (templates)
        and values are dictionaries. Keys of these dictionaries are
        counter names (with queue ID filled), values are units.
    """

    xstats: dict[str, CounterUnit]
    xstats_per_q: dict[str, dict[str, CounterUnit]]


class RxTxStats:
    """Class for Rx/Tx statistics definition and recording.

    Note: Only extended statistics are used as all counters from basic
    statistics are contained in extended statistics already.

    Attributes
    ----------
    _config : RxTxStatsConf
        Contains statistics configuration.
        Statistics configuration consists of two dictionaries - one for
        extended statistics and per-queue extended statistics.
        Dictionaries stores counter names and related unit.
    _data : dict
        Is a storage for monitored statistics (with timestamp).
    """

    """Listing of supported extended global statistics."""
    _SUPPORTED_XSTATS = {
        "rx_good_packets": CounterUnit.PACKETS,
        "tx_good_packets": CounterUnit.PACKETS,
        "rx_good_bytes": CounterUnit.BYTES,
        "tx_good_bytes": CounterUnit.BYTES,
        "rx_missed_errors": CounterUnit.PACKETS,
        "rx_errors": CounterUnit.PACKETS,
        "tx_errors": CounterUnit.PACKETS,
        "rx_mbuf_allocation_errors": CounterUnit.PACKETS,
        "rx_unicast_bytes": CounterUnit.BYTES,
        "rx_multicast_bytes": CounterUnit.BYTES,
        "rx_broadcast_bytes": CounterUnit.BYTES,
        "rx_unicast_packets": CounterUnit.PACKETS,
        "rx_multicast_packets": CounterUnit.PACKETS,
        "rx_broadcast_packets": CounterUnit.PACKETS,
        "tx_unicast_bytes": CounterUnit.BYTES,
        "tx_multicast_bytes": CounterUnit.BYTES,
        "tx_broadcast_bytes": CounterUnit.BYTES,
        "tx_unicast_packets": CounterUnit.PACKETS,
        "tx_multicast_packets": CounterUnit.PACKETS,
        "tx_broadcast_packets": CounterUnit.PACKETS,
        "rx_wqe_errors": CounterUnit.PACKETS,
        "rx_phy_crc_errors": CounterUnit.PACKETS,
        "rx_phy_in_range_len_errors": CounterUnit.PACKETS,
        "rx_phy_symbol_errors": CounterUnit.PACKETS,
        "tx_phy_errors": CounterUnit.PACKETS,
        "dev_internal_queue_oob": CounterUnit.PACKETS,
        "tx_phy_packets": CounterUnit.PACKETS,
        "rx_phy_packets": CounterUnit.PACKETS,
        "tx_phy_discard_packets": CounterUnit.PACKETS,
        "rx_phy_discard_packets": CounterUnit.PACKETS,
        "rx_prio0_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio1_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio2_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio3_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio4_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio5_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio6_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio7_buf_discard_packets": CounterUnit.PACKETS,
        "rx_prio0_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio1_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio2_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio3_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio4_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio5_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio6_cong_discard_packets": CounterUnit.PACKETS,
        "rx_prio7_cong_discard_packets": CounterUnit.PACKETS,
        "tx_phy_bytes": CounterUnit.BYTES,
        "rx_phy_bytes": CounterUnit.BYTES,
        "rx_pci_signal_integrity": CounterUnit.OTHER,
        "tx_pci_signal_integrity": CounterUnit.OTHER,
        "outbound_pci_stalled_rd": CounterUnit.OTHER,
        "outbound_pci_stalled_wr": CounterUnit.OTHER,
        "outbound_pci_stalled_rd_events": CounterUnit.OTHER,
        "outbound_pci_stalled_wr_events": CounterUnit.OTHER,
        "rx_out_of_buffer": CounterUnit.PACKETS,
        "hairpin_out_of_buffer": CounterUnit.PACKETS,
        "tx_pp_missed_interrupt_errors": CounterUnit.OTHER,
        "tx_pp_rearm_queue_errors": CounterUnit.OTHER,
        "tx_pp_clock_queue_errors": CounterUnit.OTHER,
        "tx_pp_timestamp_past_errors": CounterUnit.OTHER,
        "tx_pp_timestamp_future_errors": CounterUnit.OTHER,
        "tx_pp_timestamp_order_errors": CounterUnit.OTHER,
        "tx_pp_jitter": CounterUnit.OTHER,
        "tx_pp_wander": CounterUnit.OTHER,
        "tx_pp_sync_lost": CounterUnit.OTHER,
    }

    """Listing of supported extended per-queue statistics."""
    _SUPPORTED_XSTATS_PER_Q = {
        "rx_q{q_id}_packets": CounterUnit.PACKETS,
        "rx_q{q_id}_errors": CounterUnit.PACKETS,
        "tx_q{q_id}_packets": CounterUnit.PACKETS,
        "rx_q{q_id}_bytes": CounterUnit.BYTES,
        "tx_q{q_id}_bytes": CounterUnit.BYTES,
    }

    """Default counters to monitor."""
    DEFAULT_STATS = StatsRequest(
        xstats=(
            "rx_good_packets",  # rx_packets
            "rx_missed_errors",  # rx_missed
            "rx_errors",  # rx_errors
            "rx_mbuf_allocation_errors",  # rx_nombuf
            "tx_good_packets",  # tx_packets
            "tx_errors",  # tx_errors
            "rx_phy_packets",
            "rx_phy_discard_packets",
            "rx_phy_crc_errors",
            "rx_phy_in_range_len_errors",
            "rx_phy_symbol_errors",
            "rx_out_of_buffer",
            "tx_phy_discard_packets",
            "tx_phy_packets",
            "tx_phy_errors",
        ),
        xstats_per_q=(
            "rx_q_packets",
            "rx_q_errors",
            "tx_q_packets",
        ),
    )

    """Name of timestamp column."""
    TIMESTAMP_COL = "timestamp"

    @staticmethod
    def _per_q_stat_lookup(stat: tuple[str], lookup_group: dict[str, str]) -> str | None:
        for k in lookup_group.keys():
            if stat == k.replace("{q_id}", ""):
                return k

        return None

    def _verify_supported(self, stats_req: StatsRequest):
        for s in stats_req.xstats:
            if s not in RxTxStats._SUPPORTED_XSTATS.keys():
                raise ValueError(f"{s} is not a supported name in extended statistics")

        for s in stats_req.xstats_per_q:
            if not self._per_q_stat_lookup(s, RxTxStats._SUPPORTED_XSTATS_PER_Q):
                raise ValueError(f"{s} is not a supported name in per-queue extended statistics")

    @staticmethod
    def _y_label_from_unit(unit: CounterUnit) -> str:
        if unit == CounterUnit.PACKETS:
            return "pps (approximated)"
        elif unit == CounterUnit.BYTES:
            return "Bps (approximated)"
        return "<events>"

    def _init_stats_per_q(
        self,
        stats_per_q: tuple[str],
        q_cnt: int,
        lookup_group: dict[str, str],
    ) -> dict[str, dict[str, CounterUnit]]:
        result = dict()
        for sq in stats_per_q:
            s_tmplt = self._per_q_stat_lookup(sq, lookup_group)
            sq_group = dict()
            for i in range(q_cnt):
                sq_group[s_tmplt.format(q_id=i)] = lookup_group[s_tmplt]
            result[s_tmplt.format(q_id="")] = sq_group
        return result

    def __init__(self, stats_req: StatsRequest, q_cnt: int):
        self._verify_supported(stats_req)

        xs = {k: RxTxStats._SUPPORTED_XSTATS[k] for k in stats_req.xstats}
        xs_per_q = self._init_stats_per_q(
            stats_req.xstats_per_q,
            q_cnt,
            RxTxStats._SUPPORTED_XSTATS_PER_Q,
        )
        self._config = RxTxStatsConf(xstats=xs, xstats_per_q=xs_per_q)

        per_q_keys = [k for sq_group in self._config.xstats_per_q.values() for k in sq_group.keys()]
        keys = tuple(self._config.xstats.keys()) + tuple(per_q_keys)
        assert len(keys) == len(set(keys)), "Duplicate counter names are not supported."

        self._data = {k: [] for k in (self.TIMESTAMP_COL,) + keys}

    def get_config(self) -> RxTxStatsConf:
        """Get current configuration.

        Returns
        -------
        RxTxStatsConf
            Returns statistics configuration.
        """

        return self._config

    def _store_stats_group(
        self,
        source: dict[str, int | float] | None,
        group: dict[str, CounterUnit],
    ):
        for k in group.keys():
            if not source:
                self._data[k].append(0)
            else:
                self._data[k].append(source[k])

    def store_stats(
        self,
        timestamp: int,
        xstats: dict[str, int | float] | None,
    ):
        """Store statistics from single monitoring step.

        As all monitored statistics are incremental, difference between
        previous and current value is computed for every counter. Bytes
        or packets count are then approximated to bytes-per-second or
        packets-per-second values.

        Parameters
        ----------
        timestamp : int
            Timestamp of a monitoring step.
        xstats : dict
            Extended statistics.
        """

        self._data[self.TIMESTAMP_COL].append(timestamp)

        self._store_stats_group(xstats, self._config.xstats)
        for stats_group in self._config.xstats_per_q.values():
            self._store_stats_group(xstats, stats_group)

    def get_data(self) -> dict[str, list[int | float]]:
        """Retrieve stored statistics.

        Returns
        -------
        dict
            Dictionary with counter names as keys and list of monitoring
            measurements as values.
        """

        return self._data


class ProfiledPipelineWithStatsSubject(ProfiledPipelineSubject):
    """Subject of profiling with support for monitoring of selected
    Rx/Tx statistics.

    """

    def __init__(
        self,
        pipeline: PipelineRuntime,
        stats_req: StatsRequest = RxTxStats.DEFAULT_STATS,
    ):
        super().__init__(pipeline)
        self._stats = RxTxStats(stats_req, pipeline.get_workers_count())

    def stats(self) -> RxTxStats:
        return self._stats


class RxTxMonProfiler(ThreadedProfiler):
    """Profiler that is running a thread that continuously collects data
    about Rx/Tx bytes and packets.

    Profiler monitors selected Rx/Tx counters from extended statistics.
    Recorded results are stored as a CSV and interactive charts (html
    page).
    """

    def __init__(
        self,
        time_step: float = 0.1,
        **kwargs,
    ):
        """
        Parameters
        ----------
        time_step : float, optional
            Measurements step as fraction of seconds.
        kwargs
            Options to pass to ThreadedProfiler initializer.
        """

        super().__init__(**kwargs)

        self._time_step = time_step

    def start(self, subject: ProfiledPipelineWithStatsSubject):
        if not isinstance(subject, ProfiledPipelineWithStatsSubject):
            raise RuntimeError("subject must be of type ProfiledPipelineWithStatsSubject")
        super().start(subject)

    def mark(self, desc=None):
        self._marker.mark(time.monotonic(), desc)

    @staticmethod
    def _stat_name_postprocessed(stat_name: str) -> str:
        return f"{stat_name}_postprocessed"

    @staticmethod
    def _specs_per_unit(stats: dict[str, CounterUnit]) -> dict[CounterUnit, list[str]]:
        per_unit = dict()
        for s, unit in stats.items():
            if unit not in per_unit:
                per_unit[unit] = []
            per_unit[unit].append(s)

        return per_unit

    def _create_charts_spec(
        self,
        config: RxTxStatsConf,
    ) -> list[charts.SubPlotSpec]:
        """Create charts specification.

        Returns
        -------
        charts_spec : list(charts.SubPlotSpec)
            A list of charts specifications. There will be one chart for
            each used counter unit for basic statistics, one chart for
            each used counter unit for extended statistics and one chart
            for each used per-queue counter.
        """

        ch_spec = []

        for unit, columns in self._specs_per_unit(config.xstats).items():
            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"Extended Statistics ({unit})",
                    y_label=RxTxStats._y_label_from_unit(unit),
                    columns=[self._stat_name_postprocessed(c) for c in columns],
                )
            )

        for title, sq_group in config.xstats_per_q.items():
            unit = next(iter(sq_group.values()))  # all items in a group have same value
            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"{title} (per queue)",
                    y_label=RxTxStats._y_label_from_unit(unit),
                    columns=[self._stat_name_postprocessed(c) for c in sq_group.keys()],
                    col_names=list(range(len(sq_group))),
                )
            )

        return ch_spec

    def _restore_stats_reading(self, initial_pid: int, timeout: int = 10):
        last_unavailable = None

        def _pipeline_is_active():
            try:
                self._subject.get_pipeline().wait_until_active()
                return True
            except OSError:
                nonlocal last_unavailable
                last_unavailable = time.monotonic()
                return False

        t1 = time.time()
        common.wait_until_condition(_pipeline_is_active, timeout, sleep_step=self._time_step)

        self._subject.stats().store_stats(last_unavailable, None)  # outage end

        curr_pid = self._subject.get_pipeline().get_pid()
        stats = self._subject.get_pipeline().get_xstats()

        if initial_pid != curr_pid:
            self.mark(desc="Pipeline restarted")
            self._logger.info(
                f"Pipeline has been restarted (PID changed): {initial_pid} -> {curr_pid}."
            )
            self._logger.info(f"Statistics reading restored after {time.time() - t1:.2f}s.")

        return stats, curr_pid

    def _data_collect(self) -> tuple[pandas.DataFrame, RxTxStatsConf]:
        pipeline = self._subject.get_pipeline()
        stats_storage = self._subject.stats()

        pipeline.wait_until_active()
        pid = pipeline.get_pid()

        while not self.wait_stoppable(self._time_step):
            try:
                p_xstats = pipeline.get_xstats()
            except OSError:
                stats_storage.store_stats(time.monotonic(), None)  # outage start
                p_xstats, pid = self._restore_stats_reading(pid)

            stats_storage.store_stats(time.monotonic(), p_xstats)

        self._logger.info(f"sampled {len(stats_storage.get_data())}x Rx/Tx statistics")

        return pandas.DataFrame(stats_storage.get_data()), stats_storage.get_config()

    @staticmethod
    def _postprocess_stats_group(stats, group, time_steps):
        for col, unit in group.items():
            prev = None
            new_col = []

            for i in range(len(stats[col])):
                val = stats[col].iloc[i]
                if val == 0:  # no measurement available (start or outage )
                    new_col.append(0)
                    prev = None
                    continue

                if not prev:  # counter reset (beginning of measurement)
                    prev = val

                pp_val = val - prev
                prev = val
                if unit == CounterUnit.PACKETS or unit == CounterUnit.BYTES:
                    if time_steps[i] == 0:
                        new_col.append(0)
                    else:
                        per_second_approx = (1 / time_steps[i]) * pp_val
                        new_col.append(per_second_approx)
                else:
                    new_col.append(pp_val)

            pp_col = RxTxMonProfiler._stat_name_postprocessed(col)
            assert pp_col not in stats.columns
            stats[pp_col] = new_col

    @staticmethod
    def _compute_time_steps(timestamps: pandas.Series) -> pandas.Series:
        """Compute time-steps between two consequent measurements.

        Waiting for defined time step might not be exact, we compute
        real duration of time step. As there is no "previous" value
        for first timestamp, first time-step is always zero.

        Parameters
        ----------
        timestamps: pandas.Series
            Series of timestamps from which time-steps are computed.

        Returns
        -------
        pandas.Series
            Series of computed time-steps (length is as same as length
            of timestamps Series).
        """

        first_prev = timestamps[0]  # first value will be zero after subtraction
        return timestamps - timestamps.shift(1, fill_value=first_prev)

    def _data_postprocess(self, data: pandas.DataFrame, config: RxTxStatsConf):
        time_steps = self._compute_time_steps(data[RxTxStats.TIMESTAMP_COL])
        self._postprocess_stats_group(data, config.xstats, time_steps)
        for stats_group in config.xstats_per_q.values():
            self._postprocess_stats_group(data, stats_group, time_steps)

        markers = self._marker.to_dataframe()
        markers["time"] = self._make_timestamps_relative(
            markers["time"],
            data[RxTxStats.TIMESTAMP_COL].min(),
        )

        data[RxTxStats.TIMESTAMP_COL] = self._make_timestamps_relative(
            data[RxTxStats.TIMESTAMP_COL],
        )
        charts.create_charts_html(
            data,
            self._create_charts_spec(config),
            self.charts_file(),
            title="Rx/Tx Statistics",
            markers=markers,
        )
