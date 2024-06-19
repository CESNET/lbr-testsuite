"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023-2024 CESNET, z.s.p.o.

Module describing DPDK port and its operations.
"""

import json
import socket
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path

from lbr_testsuite import wait_until_condition


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
