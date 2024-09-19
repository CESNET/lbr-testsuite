"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Implementation of profiler measuring power consumption by pyJoules library.
"""

import logging

from pyJoules.device import DeviceFactory
from pyJoules.device.rapl_device import RaplDevice
from pyJoules.energy_meter import EnergyMeter
from pyJoules.handler.pandas_handler import PandasHandler

from .profiler import ThreadedProfiler


global_logger = logging.getLogger(__name__)


class pyJoulesProfiler(ThreadedProfiler):
    """Profiler that is running a thread that continuously collects data
    about power consumption of the system by using pyJoules framework.
    """

    def __init__(self, csv_file, png_file, numa_sockets=None, time_step=1):
        """
        Parameters
        ----------
        csv_file : str | Path
            Where to store generated CSV file.
        png_file : str | Path
            Where to store generated PNG file (plot).
        numa_sockets : list[int], optional
            List of NUMA sockets to measure. When omitted, NUMA autodetection is used.
        time_step : double
            Data collection frequency (time period) in seconds.
        """

        super().__init__()

        self._csv_file = csv_file
        self._png_file = png_file
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

    def run(self):
        """This method should be started from a thread. It snapshots power consumption
        metrics periodically according to time_step. Finally, CSV and PNG files are generated.
        """

        domains_repr = [repr(domain) for domain in self._domains]
        self._meter.start(self.get_thread().name)
        global_logger.info(f"measuring power consumption (domains: {domains_repr})...")

        try:
            while not self.wait_stoppable(self._time_step):
                global_logger.debug("record power consumption status")
                self._meter.record(self.get_thread().name)
        finally:
            self._meter.stop()

        global_logger.info(f"saving to {self._csv_file} and {self._png_file}")

        handler = PandasHandler()
        try:
            handler.process(self._meter.get_trace())
        finally:
            df = handler.get_dataframe().iloc[:-1]  # drop last, it is too close to second last
            df.to_csv(self._csv_file)

            global_logger.debug("plotting power consumption...")

            df["timestamp"] = self._make_timestamps_relative(df["timestamp"])
            p = df.plot(
                title="Power Consumption",
                xlabel="time [s]",
                ylabel="consumption [uJ]",
                kind="bar",
                x="timestamp",
                y=domains_repr,
                legend=True,
            )
            p.get_figure().savefig(self._png_file)
            global_logger.debug("power consumption chart has been saved")
