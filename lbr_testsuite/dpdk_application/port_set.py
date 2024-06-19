"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Module containing a class for grouping DPDK ports together.
"""

import collections

from .dpdk_port import DPDKPort


class DPDKPortSet:
    """Abstract class representing a set of DPDK ports.

    Note that all ports must have the same duplex configuration,
    otherwise it makes no sense to aggregate them.

    Attributes
    ----------
    ports : list(DPDKPort)
        List of DPDK ports.
    """

    def __init__(self, ports: list):
        self._ports = ports

    def __len__(self) -> int:
        """Get length of the port set.

        Returns
        -------
        int
            Length of the port set (i.e. count of ports in set).
        """

        return len(self._ports)

    def _aggregate_stats(self, extended=False):
        total = collections.Counter()

        for port in self._ports:
            if extended:
                stats = port.get_xstats()
            else:
                stats = port.get_stats()
            total.update(stats)

        return dict(total)

    def get_stats(self) -> dict:
        """Aggregate DPDK port statistics from all ports.

        Since each port can return a dictionary of tuples
        with individual port statistics, it is necessary
        to "merge" the tuples together. This is done by the
        zip and sum functions.

        Returns
        -------
        dict
            Dictionary with port statistics aggregated from all ports.
        """

        return self._aggregate_stats()

    def clear_stats(self):
        """Clear statistics on all ports."""

        for port in self._ports:
            port.clear_stats()

    def get_xstats(self) -> dict:
        """Aggregate extended statistics from all ports.

        Returns
        -------
        dict
            Dictionary with aggregated extended statistics from all
            ports.
        """

        return self._aggregate_stats(extended=True)

    def clear_xstats(self):
        """Clear extended statistics on all ports."""

        for port in self._ports:
            port.clear_xstats()

    @staticmethod
    def _ports_duplex(statuses):
        first = statuses[0]

        # Check that link configuration is equal
        for i in statuses:
            if i["duplex"] != first["duplex"]:
                raise RuntimeError(
                    f"Non-matching duplex mode detected: {i['duplex']} does not equal "
                    f"{first['duplex']}."
                )

        return first["duplex"]

    def get_status(self) -> dict:
        """Aggregate port status from all ports into a single
        dictionary.

        Note that link status can only be UP when all ports are UP.
        Otherwise, DOWN is reported.

        The resulting dictionary follows the format:
        ```
        {
            "speed": int,
            "duplex": str,
            "status": str,
        }
        ```

        Returns
        -------
        dict
            Dictionary with aggregated port status.

        Raises
        ------
        RuntimeError
            The individual ports have not been configured the same way.
        """

        statuses = [i.get_status() for i in self._ports]

        # Derive link state
        if all(x["port"] == "UP" for x in statuses):
            state = "UP"
        else:
            state = "DOWN"

        return {
            "speed": sum([int(x["speed"]) for x in statuses]),
            "duplex": self._ports_duplex(statuses),
            "status": state,
        }

    def get_port(self, index) -> DPDKPort:
        """Get single port from set of ports by its index.

        Parameters
        ----------
        index : int
            Index of requested port.

        Returns
        -------
        DPDKPort
            Requested port.
        """

        return self._ports[index]
