"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Base class for running throughput tests
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from lbr_testsuite.profiling.profiler import PackedProfiler
from lbr_testsuite.spirent.spirent import Spirent
from lbr_testsuite.spirent.stream_block import StreamBlock


@dataclass
class ThroughputRunnerMeasurementData:
    """Data class storing data from a throughput measurement.

    Parameters
    ----------
    tx : int
        Count of packets transmitted from a generator (TX).
    rx : int
        Count of packets received on an analyzer (might be as same
        as generator; RX).
    """

    tx: int = None
    rx: str = None


class SpirentThroughputRunner:
    """Runner class responsible for executing Spirent throughput tests."""

    def __init__(
        self,
        spirent: Spirent,
        stream_blocks: List[StreamBlock],
        profiler: Optional[PackedProfiler] = None,
    ):
        """
        Parameters
        ----------
        spirent : Spirent
            Instance of configured spirent generator object.
        stream_blocks : list
            List of stream blocks used to generate traffic.
        profiler : PackedProfiler, default None
            Instance of profiler. Can be None.
        """

        self._spirent = spirent
        self._stream_blocks = stream_blocks
        self._logger = logging.getLogger(self.__class__.__name__)

        if profiler is None:
            self._profiler = PackedProfiler()
        else:
            self._profiler = profiler

        self._spirent.deactivate_all_stream_blocks()
        for block in stream_blocks:
            block.set_active(True)

        self._last_measurement = ThroughputRunnerMeasurementData()

    def _warm_up(self):
        """Generate a short burst of packets before the actual
        test to warm up caches.
        """

        self._spirent._stc_handler.stc_clear_results()
        self._spirent.generate_traffic(0.2)

        for block in self._stream_blocks:
            stats = block.get_tx_rx_stats()
            tx = stats["tx"]["FrameCount"]
            assert tx > 0, "No packets transmitted."

    def _pre_test_traffic_gen(self):
        """Execute some steps before test traffic generating.

        Note: Method is not used here. Its purpose is to provide
        finer control for derived classes.
        """
        ...

    def _evaluate_stream_block(self, block: StreamBlock) -> Tuple[int, int]:
        """Evaluate spirent statistics for given stream block.

        Parameters
        ----------
        block : StreamBlock
            Evaluated stream block.

        Returns
        -------
        tuple
            Tuple containing the TX and RX packets counts.
        """

        stats = block.get_tx_rx_stats()
        tx = stats["tx"]["FrameCount"]
        rx = stats["rx"]["FrameCount"]

        self._logger.debug(f"Stream block '{block.name()}':")
        self._logger.debug(
            f"TX: {tx} frames (100 %), "
            f"RX: {rx} frames ({rx / tx:.1%}), "
            f"diff: {tx - rx} frames ({(tx - rx) / tx:.1%})"
        )
        assert tx > 0, "No packets transmitted"
        assert rx > 0, "No packets received"
        assert rx <= tx, "Received more packets than transmitted"

        return tx, rx

    def generate_traffic(
        self,
        load_mbps: int,
        packet_len: int,
        duration: Optional[int] = 5,
    ):
        """Generate traffic from a spirent instance for a given
        number of seconds.

        Parameters
        ----------
        load_mbps : int, optional
            Total requested spirent load. If not set, it is
            assumed that the stream block load is configured.
        packet_len : int, optional
            Requested packet length. If not set, it is assumed
            that the packet length is configured in each stream
            block.
        duration : int
            Duration of generated traffic in seconds.
        """

        self._spirent._stc_handler.stc_set_port_scheduling_mode("port")
        self._spirent.set_port_load("mbps", load_mbps)

        if packet_len is not None:
            for block in self._stream_blocks:
                block.set_packet_len(packet_len)

        for block in self._stream_blocks:
            block.apply()

        self._warm_up()

        self._profiler.start()
        self._pre_test_traffic_gen()

        # Main test traffic
        self._spirent._stc_handler.stc_clear_results()

        self._profiler.mark()
        self._spirent.generate_traffic(duration)
        self._profiler.stop()

        self._logger.debug(f"Measured load {load_mbps} Mbps:")

    def evaluate(self) -> Tuple[int, int]:
        """Evaluate traffic generation by reading spirent's counters.

        Returns
        -------
        tuple
            Tuple containing the TX and RX numbers of packets.
        """

        total_tx = 0
        total_rx = 0

        for block in self._stream_blocks:
            tx, rx = self._evaluate_stream_block(block)
            total_tx += tx
            total_rx += rx

        self._last_measurement.tx = total_tx
        self._last_measurement.rx = total_rx
        return self._last_measurement.tx, self._last_measurement.rx

    def _no_packet_missed(self) -> bool:
        return self._last_measurement.tx == self._last_measurement.rx

    def measure_max(
        self,
        max_load_mbps: int,
        packet_len: int,
        precision_mbps: Optional[int] = 100,
    ) -> Tuple[int, int]:
        """Measure maximum zero packet loss throughput using binary search.

        Parameters
        ----------
        max_load_mbps : int
            Maximum measured load in megabits per second.
        precision_mbps : int
            Minimum difference between two consecutive binary search attempts.

        Returns
        -------
        tuple
            Tuple of (mbps, mpps) representing the maximum measured throughput
            in megabits and megapackets per second.
        """

        upper_bound = max_load_mbps
        lower_bound = 0
        test_load = max_load_mbps
        duration = 5

        while upper_bound - lower_bound > precision_mbps:
            self.generate_traffic(test_load, packet_len, duration)
            self.evaluate()
            if self._no_packet_missed():
                lower_bound = test_load
            else:
                upper_bound = test_load

            test_load = (upper_bound + lower_bound) // 2

        throughput_mpps = (self._last_measurement.rx / duration) / 1000000

        return lower_bound, throughput_mpps
