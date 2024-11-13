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

from . import _charts as charts
from .pipeline import ProfiledPipelineSubject
from .profiler import ProfilerMarker, ThreadedProfiler


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


class RxTxStats:
    """Class for Rx/Tx statistics definition and recording.

    Note: Only extended statistics are used as all counters from basic
    statistics are contained in extended statistics already.

    Attributes
    ----------
    _timestamp : str
        Name of timestamp counter.
    _xstats : dict
        Dictionary with selected counters from extended statistics. Keys
        are counter names, values are units.
    _xstats_per_q : dict
        Dictionary with selected counters from extended statistics for
        for every queue. Keys are general counter names (templates)
        and values are dictionaries. Keys of these dictionaries are
        counter names (with queue ID filled), values are units.
    _charts_spec : list(charts.SubPlotSpec)
        A list of charts specifications. There will be one chart for
        each used counter unit for basic statistics, one chart for
        each used counter unit for extended statistics and one chart
        for each used per-queue counter.
    _data : dict
        Is a storage for monitored statistics (with timestamp).
    _last : dict
        Is a storage with last values of monitored statistics.
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

    @staticmethod
    def _per_q_stat_lookup(stat, lookup_group):
        for k in lookup_group.keys():
            if stat == k.replace("{q_id}", ""):
                return k

        return None

    def _verify_supported(self, stats_req):
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

    @staticmethod
    def _specs_per_unit(stats):
        per_unit = dict()
        for s, unit in stats.items():
            if unit not in per_unit:
                per_unit[unit] = []
            per_unit[unit].append(s)

        return per_unit

    def _create_charts_spec(self, q_cnt):
        ch_spec = []

        for unit, columns in self._specs_per_unit(self._xstats).items():
            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"Extended Statistics ({unit})",
                    y_label=self._y_label_from_unit(unit),
                    columns=columns,
                )
            )

        for title, sq_group in self._xstats_per_q.items():
            unit = next(iter(sq_group.values()))  # all items in a group have same value
            ch_spec.append(
                charts.SubPlotSpec(
                    title=f"{title} (per queue)",
                    y_label=self._y_label_from_unit(unit),
                    columns=list(sq_group.keys()),
                    col_names=list(range(q_cnt)),
                )
            )

        return ch_spec

    def _init_stats_per_q(self, stats_per_q, q_cnt, lookup_group):
        result = dict()
        for sq in stats_per_q:
            s_tmplt = s_tmplt = self._per_q_stat_lookup(sq, lookup_group)
            sq_group = dict()
            for i in range(q_cnt):
                sq_group[s_tmplt.format(q_id=i)] = lookup_group[s_tmplt]
            result[s_tmplt.format(q_id="")] = sq_group
        return result

    def __init__(self, stats_req: StatsRequest, q_cnt: int):
        self._verify_supported(stats_req)

        self._timestamp = "timestamp"

        self._xstats = {k: RxTxStats._SUPPORTED_XSTATS[k] for k in stats_req.xstats}
        self._xstats_per_q = self._init_stats_per_q(
            stats_req.xstats_per_q,
            q_cnt,
            RxTxStats._SUPPORTED_XSTATS_PER_Q,
        )

        per_q_keys = [k for sq_group in self._xstats_per_q.values() for k in sq_group.keys()]
        keys = tuple(self._xstats.keys()) + tuple(per_q_keys)
        assert len(keys) == len(set(keys)), "Duplicate counter names are not supported."
        self._data = {k: [] for k in (self._timestamp,) + keys}
        self._last = {k: 0 for k in keys}

        self._charts_spec = self._create_charts_spec(q_cnt)

    def xstats(self) -> dict:
        """Get specification of monitored extended global statistics.

        Returns
        -------
        dict
            Dictionary with selected counters from extended statistics.
            Keys are counter names, values are units.
        """

        return self._xstats

    def xstats_per_q(self) -> dict:
        """Get specification of monitored extended per-queue statistics.

        Returns
        -------
        dict
            Dictionary with selected counters from extended statistics
            for every queue. Keys are general counter names (templates)
            and values are dictionaries. Keys of these dictionaries are
            counter names (with queue ID filled), values are units.
        """

        return self._xstats_per_q

    def get_chart_spec(self) -> tuple:
        """Get charts specification.

        Returns
        -------
        list(charts.SubPlotSpec)
            A list of charts specifications.
        """

        return self._charts_spec

    def _store_stats_group(self, source: dict, group: dict, time_step: float):
        for k, unit in group.items():
            val = source[k] - self._last[k]
            self._last[k] = source[k]
            if unit == CounterUnit.PACKETS or CounterUnit.BYTES:
                per_second_approx = (1 / time_step) * val
                self._data[k].append(per_second_approx)
            else:
                self._data[k].append(val)

    def store_stats(self, timestamp: int, xstats: dict, time_step: float):
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
        time_step : float
            Monitoring step length as a count of seconds (or fraction of
            second).
        """

        self._data[self._timestamp].append(timestamp)
        self._store_stats_group(xstats, self._xstats, time_step)
        for stats_group in self._xstats_per_q.values():
            self._store_stats_group(xstats, stats_group, time_step)

    def reset_last_counters(self, xstats: dict):
        """Reset last values of counters.

        Typically, this method should be called at the very beginning of
        statistics monitoring. Without calling of this method, first
        stored values might show significant peak as counters will
        contain values since start of an application until the first
        monitoring step.

        Parameters
        ----------
        xstats : dict
            Extended statistics.
        """

        for k in self._last.keys():
            self._last[k] = xstats[k]

    def get_data(self) -> dict:
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
        csv_file: str,
        mark_file: str,
        charts_file: str,
        time_step: float = 0.1,
    ):
        """
        Parameters
        ----------
        csv_file : str
            Path to a CSV file with measured values.
        mark_file : str
            Path to a mark file.
        charts_file : str
            Path to a file with charts.
        time_step : float, optional
            Measurements step as fraction of seconds.
        """

        super().__init__()

        self._csv_file = csv_file
        self._mark_file = mark_file
        self._charts_file = charts_file
        self._time_step = time_step
        self._marker = ProfilerMarker()

    def start(self, subject: ProfiledPipelineWithStatsSubject):
        if not isinstance(subject, ProfiledPipelineWithStatsSubject):
            raise RuntimeError("subject must be of type ProfiledPipelineWithStatsSubject")
        super().start(subject)

    def mark(self):
        self._marker.mark(time.monotonic())

    def run(self):
        pipeline = self._subject.get_pipeline()
        stats_storage = self._subject.stats()

        pipeline.wait_until_active()

        stats_storage.reset_last_counters(pipeline.get_xstats())
        while not self.wait_stoppable(self._time_step):
            stats_storage.store_stats(
                time.monotonic(),
                pipeline.get_xstats(),
                self._time_step,
            )

        self._logger.info(f"sampled {len(stats_storage.get_data())}x Rx/Tx statistics")

        df = pandas.DataFrame(stats_storage.get_data())
        df.to_csv(self._csv_file)

        with open(self._mark_file, "w") as f:
            self._marker.save(f)

        df["timestamp"] = self._make_timestamps_relative(df["timestamp"])
        markers = self._make_timestamps_relative(pandas.Series([m for m in self._marker]))
        charts.create_charts_html(
            df,
            stats_storage.get_chart_spec(),
            self._charts_file,
            title="Rx/Tx Statistics",
            markers=list(markers),
        )
