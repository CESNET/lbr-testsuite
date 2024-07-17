"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Abstract interface that can be implemented to provide aggregated statistics.
"""

from abc import ABC, abstractmethod
from typing import Dict


class StatsInterface(ABC):
    """Abstract interface that can be implemented to provide
    aggregated statistics.
    """

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Obtain implementation specific statistics.

        The output format is expected to look like this:
        ```
        "rx_packets": 0,
        "rx_bytes": 0,
        "rx_missed": 0,
        "rx_errors": 0,
        "rx_nombuf": 0,
        "tx_packets": 0,
        "tx_bytes": 0,
        "tx_errors": 0,
        "rx0_packets": 0
        "rx0_bytes": 0
        "rx0_errors": 0
        "tx0_packets": 0
        "tx0_bytes": 0
        ...
        ```

        The un-numbered keys represent total statistics,
        while keys with a number (e.g. rx0_*, tx0_*) correspond
        to a specific RX or TX queue.

        Note that the numbered values may be omitted.

        Returns
        -------
        Dict[str, int]
            Dictionary with statistics records.
        """

        ...

    @abstractmethod
    def clear_stats(self) -> None:
        """Clear implementation specific statistics."""

        ...

    @abstractmethod
    def get_xstats(self) -> Dict[str, int]:
        """Obtain implementation specific extended statistics.

        The acutal ouptut format may vary but it is always
        a mapping between an xstat name and its value.

        Returns
        -------
        Dict[str, int]
            Dictionary with extended statistics.
        """

        ...

    @abstractmethod
    def clear_xstats(self) -> None:
        """Clear implementation specific extended statistics."""

        ...
