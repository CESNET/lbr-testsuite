"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Implementation of profiler measuring power consumption by pyJoules library.
"""

import logging

from pandas import DataFrame
from pyJoules.device import DeviceFactory
from pyJoules.device.rapl_device import RaplDevice
from pyJoules.energy_meter import EnergyMeter
from pyJoules.handler.pandas_handler import PandasHandler

from .._base import charts
from .._base.concurrent_profiler import ConcurrentProfiler


global_logger = logging.getLogger(__name__)


class pyJoulesProfiler(ConcurrentProfiler):
    """Profiler that is running a thread that continuously collects data
    about power consumption of the system by using pyJoules framework.
    """

    def __init__(self, numa_sockets=None, time_step=1, **kwargs):
        """
        Parameters
        ----------
        numa_sockets : list[int], optional
            List of NUMA sockets to measure. When omitted, NUMA autodetection is used.
        time_step : double
            Data collection frequency (time period) in seconds.
        kwargs
            Options to pass to ConcurrentProfiler initializer.
        """

        super().__init__(**kwargs)

        self._time_step = time_step
        self._domains = []

        def accept_socket(domain):
            if numa_sockets is None:
                return True

            return domain.socket in numa_sockets

        self._domains.extend(filter(accept_socket, RaplDevice.available_package_domains()))
        self._domains.extend(filter(accept_socket, RaplDevice.available_dram_domains()))
        self._domains.extend(filter(accept_socket, RaplDevice.available_core_domains()))
        self._domains.extend(filter(accept_socket, RaplDevice.available_uncore_domains()))

        devices = DeviceFactory.create_devices(self._domains)
        self._meter = EnergyMeter(devices)

    def _make_timestamps_relative(self, timestamps):
        return timestamps.sub(timestamps.min()).add(1).round().astype("int64")

    def _data_collect(self) -> tuple[DataFrame, list[str]]:
        """This method should be started from a thread. It snapshots
        power consumption metrics periodically according to time_step.
        Finally, CSV and charts files are generated in _data_postprocess
        method.
        """

        domains_repr = [repr(domain) for domain in self._domains]
        self._meter.start(self.get_name())
        global_logger.info(f"measuring power consumption (domains: {domains_repr})...")

        try:
            while not self.wait_stoppable(self._time_step):
                global_logger.debug("record power consumption status")
                self._meter.record(self.get_name())
        finally:
            self._meter.stop()

        handler = PandasHandler()
        try:
            handler.process(self._meter.get_trace())
        finally:
            df = handler.get_dataframe().iloc[:-1]  # drop last, it is too close to second last

            return df, domains_repr

    def _data_postprocess(self, data: DataFrame, domains_repr: list[str]):
        global_logger.debug("plotting power consumption...")

        data["timestamp"] = self._make_timestamps_relative(data["timestamp"])
        ch_spec = charts.SubPlotSpec(
            title="Power Consumption",
            y_label="consumption [uJ]",
            columns=domains_repr,
            chart_type=charts.ChartType.BAR,
        )

        charts.create_charts_html(
            data,
            ch_spec,
            self.charts_file(),
            title="Power Consumption",
        )

        global_logger.debug("power consumption chart has been saved")
