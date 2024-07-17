"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Module describing DPDK port and its operations.
"""

import json
import logging
import socket
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from typing import List, Tuple

from lbr_testsuite import wait_until_condition
from lbr_testsuite.dpdk_application.stats_interface import StatsInterface


global_logger = logging.getLogger(__name__)


class DPDKPort(ABC):
    """Abstract class representing a DPDK port."""

    def __init__(self):
        self._snapshots = dict(stats=None, xstats=None)

    @abstractmethod
    def get_mac_addr(self) -> str:
        """Obtain DPDK port MAC address

        Returns
        -------
        str
            MAC address in standard format 'XX:XX:XX:XX:XX:XX'.
        """

        pass

    @abstractmethod
    def _stats(self) -> dict:
        """Obtain DPDK port statistics."""

        pass

    @abstractmethod
    def _xstats(self) -> dict:
        """Obtain DPDK extended port statistics."""

        pass

    def get_stats(self) -> dict:
        """Obtain DPDK port statistics.

        The minimal expected format is:
        ```
        "rx" : (
            packets,
            bytes,
            missed,
            errors,
            nombuf,
        ),
        "tx" : (
            packets,
            bytes,
            errors,
        )
        ```

        Other fields might be included as well, such as
        statistics per individual queues.

        Returns
        -------
        dict
            Dictionary with DPDK port statistics.
        """

        stats = self._stats()
        if self._snapshots["stats"]:
            c = Counter(stats)
            c.subtract(self._snapshots["stats"])
            stats = dict(c)

        return stats

    def clear_stats(self):
        """Clear port statistics.

        As we are not able to clear statistics, we only simulate
        this operation by creation of a snapshot of statistics.
        The snapshot is subtracted from statistics when `get_stats` is
        called which leads to the same values as if statistics would be
        cleared in the time the snapshot was created.
        """

        self._snapshots["stats"] = self._stats()

    def get_xstats(self) -> dict:
        """Obtain DPDK extended port statistics.

        The expected format is a dictionary in the
        form xstat name, xstat value.

        Returns
        -------
        dict
            Dictionary with extended port statistics.
        """

        stats = self._xstats()
        if self._snapshots["xstats"]:
            c = Counter(stats)
            c.subtract(self._snapshots["xstats"])
            stats = dict(c)

        return stats

    def clear_xstats(self):
        """Clear extended port statistics.

        As we are not able to clear statistics, we only simulate
        this operation by creation of a snapshot of statistics.
        The snapshot is subtracted from statistics when `get_xstats` is
        called which leads to the same values as if statistics would be
        cleared in the time the snapshot was created.
        """

        self._snapshots["xstats"] = self._xstats()

    @abstractmethod
    def get_status(self) -> dict:
        """Obtain DPDK port status.

        The minimal expected result contains at least
        the link state. Other fields such as duplex
        status or port speed might also be included.

        Returns
        -------
        dict
            Dictionary with port status.
        """

        pass


class TelemetryDPDKPort(DPDKPort):
    """Class representing a DPDK port with information obtained from
    DPDK Telemetry."""

    def __init__(self, port_id: int, socket_path: Path):
        super().__init__()

        self._port_id = port_id
        self._dpdk_socket_path = socket_path

    def _query_telemetry(self, query: str) -> dict:
        timeout = 5
        if not wait_until_condition(self._dpdk_socket_path.exists, timeout):
            raise TimeoutError(f"DPDK telemetry did not initialize. Waited {timeout} seconds")

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        sock.settimeout(2)
        sock.connect(str(self._dpdk_socket_path))

        # Initially, the DPDK application sends an introduction message
        init = sock.recv(1024).decode()
        init_data = json.loads(init)
        max_len = init_data["max_output_len"]

        # Actual query
        sock.send(query.encode())
        reply = sock.recv(max_len).decode()
        data = json.loads(reply)

        sock.close()
        return data

    def get_info(self) -> dict:
        """Retrieve information about specified port using DPDK telemetry.

        Returns
        -------
        dict
            Dictionary with retrieved data.
        """

        path = "/ethdev/info"
        query = f"{path},{self._port_id}"
        return self._query_telemetry(query)[path]

    def get_mac_addr(self) -> str:
        """Retrieve port MAC address using DPDK telemetry.

        Returns
        -------
        str
            Port MAC address.
        """

        return self.get_info()["mac_addr"]

    def _stats(self) -> dict:
        """Retrieve statistics of specified port using DPDK telemetry.

        Returns
        -------
        dict
            Dictionary with retrieved data.
        """

        path = "/ethdev/stats"
        query = f"{path},{self._port_id}"
        data = self._query_telemetry(query)[path]
        # Port stats are converted to a more readable structure.
        port_stats = dict(
            rx_packets=data["ipackets"],
            rx_bytes=data["ibytes"],
            rx_missed=data["imissed"],
            rx_errors=data["ierrors"],
            rx_nombuf=data["rx_nombuf"],
            tx_packets=data["opackets"],
            tx_bytes=data["obytes"],
            tx_errors=data["oerrors"],
        )
        for i in range(len(data["q_ipackets"])):
            port_stats[f"rx{i}_packets"] = data["q_ipackets"][i]
            port_stats[f"rx{i}_bytes"] = data["q_ibytes"][i]
            port_stats[f"rx{i}_errors"] = data["q_errors"][i]
            port_stats[f"tx{i}_packets"] = data["q_opackets"][i]
            port_stats[f"tx{i}_bytes"] = data["q_obytes"][i]

        return port_stats

    def _xstats(self) -> dict:
        """Retrieve extended statistics of specified port using DPDK telemetry.

        Returns
        -------
        dict
            Dictionary with retrieved data.
        """

        path = "/ethdev/xstats"
        query = f"{path},{self._port_id}"
        return self._query_telemetry(query)[path]

    def get_status(self) -> dict:
        """Retrieve status of specified port using DPDK telemetry.

        Returns
        -------
        dict
            Dictionary with retrieved data.
        """

        path = "/ethdev/link_status"
        query = f"{path},{self._port_id}"
        data = self._query_telemetry(query)[path]

        # Key 'status' is renamed to 'port' to be compatible with Protector.
        data["port"] = data.pop("status")

        return data


def _evaluate_rx_tx_extended(
    tx_packets: int,
    rx_packets: int,
    application: StatsInterface,
) -> List[Tuple[int, str]]:
    stats = application.get_xstats()

    x_keys = [
        "rx_phy_crc_errors",
        "rx_phy_in_range_len_errors",
        "rx_phy_symbol_errors",
        "rx_phy_packets",
        "rx_phy_bytes",
        "rx_phy_discard_packets",
        "tx_phy_packets",
        "tx_phy_bytes",
        "tx_phy_discard_packets",
        "tx_phy_errors",
    ]
    for k in x_keys:
        if k not in stats:
            return []

    port_stats = application.get_stats()

    rx_phy_errors = (
        stats["rx_phy_crc_errors"]
        + stats["rx_phy_in_range_len_errors"]
        + stats["rx_phy_symbol_errors"]
    )

    global_logger.info(
        f"port rx-phy pkts {stats['rx_phy_packets']} bytes {stats['rx_phy_bytes']} "
        f"discarded {stats['rx_phy_discard_packets']} "
        f"errors {rx_phy_errors} "
    )
    global_logger.info(
        f"port tx-phy pkts {stats['tx_phy_packets']} bytes {stats['tx_phy_bytes']} "
        f"discarded {stats['tx_phy_discard_packets']} "
        f"errors {stats['tx_phy_errors']} "
    )

    gen_to_nic_lost = tx_packets - stats["rx_phy_packets"]
    nic_to_sw_lost = stats["rx_phy_packets"] - port_stats["rx_packets"]

    sw_to_nic_lost = port_stats["tx_packets"] - stats["tx_phy_packets"]
    nic_to_gen_lost = stats["tx_phy_packets"] - rx_packets

    return [
        (gen_to_nic_lost, "was lost between generator and NIC."),
        (nic_to_sw_lost, "did not make it from NIC to SW."),
        (sw_to_nic_lost, "did not make it from sw to NIC."),
        (nic_to_gen_lost, "was lost between NIC and analyzer (generator)."),
    ]


def evaluate_rx_tx_stages(tx_packets: int, rx_packets: int, application: StatsInterface):
    """Evaluate packet loss on different RX/TX stages.

    There are two stages considered by this evaluation:
    1) Traffic generator (and analyzer) - the source and the final
    destination of a test traffic.
    2) NIC - port used for receiving traffic from generator and sending
    it back.

    This function prints statistics from these stages about received and
    transmitted packets and errors. Further, if some unexpected packet
    loss occurs between some two consequent stages, it prints relevant
    warnings.

    Parameters
    ----------
    tx_packets : int
        Amount of test traffic send by a generator.
    rx_packets : int
        Amount of test traffic received by the analyzer (generator)
        (does not always has to match `tx_packets` (e.g. in the case of
        active; mitigation).
    application : StatsInterface
        Measured application implementing StatsInterface
    """

    port_stats = application.get_stats()

    global_logger.info(f"generator tx pkts {tx_packets:_}")
    global_logger.info(f"generator rx pkts {rx_packets:_}")
    global_logger.info(
        f"port rx pkts {port_stats['rx_packets']:_} bytes {port_stats['rx_bytes']:_} "
        f"missed {port_stats['rx_missed']:_} errors {port_stats['rx_errors']:_} "
        f"nombuf {port_stats['rx_nombuf']:_}"
    )
    global_logger.info(
        f"port tx pkts {port_stats['tx_packets']:_} bytes {port_stats['tx_bytes']:_} "
        f"errors {port_stats['tx_errors']:_} "
    )

    check_lost_stats = _evaluate_rx_tx_extended(tx_packets, rx_packets, application)

    for stat, desc in check_lost_stats:
        if stat > 0:
            global_logger.warning(f"{stat:_} packets {desc}")


def rx_out_of_buff_tolerance(tx: int, xstats: dict, percentage: int = 1):
    """Compute tolerance as a (small) percentage of send packets
    as RX-out-of-buffer packets.

    Parameters
    ----------
    tx : int
        Count of total packets send.
    xstats : dict
        Extended port statistics
    percentage : float, optional
        Tolerance as percentage of `tx`. Change this value only in
        special cases.

    Returns
    -------
    int or None
        Returns True when all missed packets are counted as
        "RX-out-off-buffer" packets and all of these packets are under
        the tolerance.
    """

    try:
        out_of_buff = int(xstats["rx_out_of_buffer"])
    except KeyError:
        global_logger.warning("RX out-of-buffer counter is not available.")
        return 0

    tolerated = int((tx / 100) * percentage)

    global_logger.info(f"Observed {out_of_buff:_} RX out-of-buffer packets.")
    if out_of_buff == 0:
        return 0

    global_logger.info(
        f"Tolerating at most {percentage}% ({tolerated:_}) of total {tx:_} packets "
        "as rx-out-of-buffer packets."
    )

    if out_of_buff <= tolerated:
        return out_of_buff
    else:
        global_logger.warning(
            f"There are more RX out-of-buffer {out_of_buff:_} packets than tolerated. "
            "No RX out-of-buffer will be allowed."
        )
        return 0


def evaluate_missed_packets(
    tx: int,
    rx: int,
    application: StatsInterface,
    expected_throughput: int,
):
    """Evaluate missed packets (packets have not been properly forwarded back).
    There is a small tolerance of missed packets.

    Parameters
    ----------
    tx : int
        Count of total packets sent.
    rx : int
        Count of total packets received.
    application : StatsInterface
        Object implementing the StatsInterface, typically some application object.
    expected_throughput : int
        Expected throughput value in mbps.
    """
    tx_rx_missed = tx - rx
    if tx_rx_missed > 0:
        rx_tx_ratio = rx / tx
        tolerance = rx_out_of_buff_tolerance(tx, application.get_xstats())
        assert tx_rx_missed - tolerance <= 0, (
            f"estimated throughput: {int(expected_throughput * rx_tx_ratio)} mbps "
            f"(expected {expected_throughput})"
        )

        if tx_rx_missed == tolerance:
            global_logger.info("All missed packets was RX out-of-buffer packets.")
        else:
            global_logger.info(
                "There was more RX out-of-buffer packets than "
                f"missed ({tolerance - tx_rx_missed} packets) ."
            )
