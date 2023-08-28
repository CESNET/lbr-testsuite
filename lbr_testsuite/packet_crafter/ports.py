"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Module implements interface of L4 ports format for traffic generators.
"""

from . import random_types


class L4Ports:
    """Common interface for L4 ports format.

    This class defines format of L4 ports when using high-level
    API for packet creation in traffic generators.

    Parameters
    ----------
    ports : int or tuple or list or random_types.RandomPort
        L4 ports. Can be set as:
        - int (single port)
        - tuple (range min-max)
        - list (list of ports)
        - ``random_types.RandomPort``

        If set as range, then both min and max value is considered
        to be part of range.
        If set as list, members can be of only int or tuple type.
        If set as RandomPort, it will be expanded into either
        single port or list of ports.
    """

    _SINGLE_PORT = "single-port"
    _PORT_RANGE = "port-range"
    _PORT_LIST = "port-list"

    def __init__(self, ports):
        self._random_flag = False

        if isinstance(ports, random_types.RandomPort):
            self._random_flag = True
            ports = ports.generate()
            if len(ports) == 1:
                ports = ports[0]

        self._type = None
        self._ports = ports

        def _check_port_value(ports):
            if isinstance(ports, int):
                assert 0 <= ports <= 65535, f"Incorrect port number {ports}"
                return self._SINGLE_PORT
            elif isinstance(ports, tuple):
                assert len(ports) == 2, "Range must have only 2 values: min and max"
                assert 0 <= ports[0] <= 65535, f"Incorrect min port number {ports[0]}"
                assert 0 <= ports[1] <= 65535, f"Incorrect max port number {ports[1]}"
                assert ports[0] <= ports[1], "Min port number is bigger than max port number"
                return self._PORT_RANGE

        if isinstance(ports, list):
            self._type = self._PORT_LIST
            for port in ports:
                _check_port_value(port)
        else:
            assert isinstance(
                ports, (int, tuple)
            ), "Ports must be one of following types: int, tuple or list."
            self._type = _check_port_value(ports)

    def is_single_port(self):
        """Return True if input was a single port."""

        return self._type == self._SINGLE_PORT

    def is_port_range(self):
        """Return True if input was a port range."""

        return self._type == self._PORT_RANGE

    def is_port_list(self):
        """Return True if input was a list of port."""

        return self._type == self._PORT_LIST

    def is_random(self):
        """Return True if ports are random.

        Returns
        ------
        bool
            True if ports are random, False otherwise.
        """

        return self._random_flag

    def ports(self):
        """Return ports (same format as input except for
        ``random_types.RandomPort``, which was converted either into
        int or list).

        Returns
        ------
        int or tuple or list
            L4 ports.
        """

        return self._ports

    def count(self):
        """Return number of all ports.

        If case of list, it's sum of all elements.
        Example:
            Input: [1, (300, 305), 500]
            Output: 8

        Returns
        ------
        int
            Number of ports.
        """

        def _count_simple_types(ports):
            if isinstance(ports, int):
                return 1
            elif isinstance(ports, tuple):
                return ports[1] - ports[0] + 1

        if self.is_port_list():
            cnt = 0
            for port in self._ports:
                cnt += _count_simple_types(port)
            return cnt
        else:
            return _count_simple_types(self._ports)

    def ports_as_list(self):
        """Return ports in form of list.

        Tuples are expanded.
        Example:
            Input: [1, (300, 305), 500]
            Output: [1, 300, 301, 302, 303, 304, 305, 500]

        Returns
        ------
        list(int)
            L4 ports.
        """

        if self.is_single_port():
            return [self._ports]
        elif self.is_port_range():
            return list(range(self._ports[0], self._ports[1] + 1))
        elif self.is_port_list():
            flat_list = []
            for port in self._ports:
                if isinstance(port, int):
                    flat_list.append(port)
                elif isinstance(port, tuple):
                    flat_list.extend(list(range(port[0], port[1] + 1)))

            return flat_list

    def ports_as_range(self):
        """Return ports in form of range.

        Returns
        ------
        tuple
            L4 ports.

        Raises
        ------
        AssertionError
            If ports cannot be converted to range.
            It happens if input was in form of list with gaps.
        """

        if self.is_single_port():
            return (self._ports, self._ports)
        elif self.is_port_range():
            return self._ports
        elif self.is_port_list():
            flat_list = self.ports_as_list()
            sorted_list = sorted(flat_list)
            assert sorted_list == list(
                range(sorted_list[0], sorted_list[-1] + 1)
            ), "Cannot convert this list to range (tuple)"

            return (sorted_list[0], sorted_list[-1])

    def port_generator(self):
        """Return port generator.

        Returns
        ------
        generator(int)
            Port generator.
        """

        if self.is_single_port():
            yield self._ports
        elif self.is_port_range():
            for port in range(self._ports[0], self._ports[1] + 1):
                yield port
        elif self.is_port_list():
            for port in self._ports:
                if isinstance(port, int):
                    yield port
                elif isinstance(port, tuple):
                    for p in range(port[0], port[1] + 1):
                        yield p

    def member(self, port):
        """Test if port is contained within the stored ports.

        Parameters
        ----------
        port : int
            Port number checked for membership.

        Returns
        -------
        bool
            True if port is within stored ports, false otherwise.
        """

        if self.is_single_port():
            return port == self._ports
        if self.is_port_range():
            return self._ports[0] <= port <= self._ports[1]
        if self.is_port_list():
            for i_port in self._ports:
                if isinstance(i_port, int):
                    if port == i_port:
                        return True
                elif isinstance(i_port, tuple):
                    if i_port[0] <= port <= i_port[1]:
                        return True

        return False

    def __str__(self):
        if self.is_single_port():
            return str(self._ports)
        if self.is_port_list():
            return str(self._ports)
        if self.is_port_range():
            return f"{self._ports[0]}-{self._ports[1]}"
