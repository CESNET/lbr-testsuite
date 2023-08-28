"""
Author(s): Dominik Tran <tran@cesnet.cz>, Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Random types for IP address and L4 ports.
"""

import faker


class RandomIP:
    """Class for generating random IP addresses.

    Parameters
    ----------
    count : int, optional
        Count of IP adresses to generate.
    seed : int, optional
        Seed value for pseudo-random generator.
    """

    def __init__(self, count=1, seed=None):
        self._count = count
        self._faker = faker.Faker()
        if seed is not None:
            self._faker.seed_instance(seed)

    def get_count(self):
        """Return count of IP adresses to generate.

        Returns
        ----------
        int
            Count of IP adresses to generate.
        """

        return self._count

    def generate(self, version=4):
        """Generate random IP addresses of given version.

        Parameters
        ----------
        version : int, optional
            IP address version. Supported values are 4 for IPv4 and 6 for IPv6.

        Returns
        ----------
        list(str)
            Sorted list of random IP addresses.
        """

        if version == 4:
            func = self._faker.ipv4
        elif version == 6:
            func = self._faker.ipv6
        else:
            raise RuntimeError(f"unsupported IP version: {version}")

        addrs = set()

        while len(addrs) < self._count:
            addrs.add(func())

        return sorted(addrs)


class RandomPort:
    """Class for generating random ports.

    Parameters
    ----------
    count : int, optional
        Count of ports to generate.
    seed : int, optional
        Seed value for pseudo-random generator.
    """

    def __init__(self, count=1, seed=None):
        self._count = count
        self._faker = faker.Faker()
        if seed is not None:
            self._faker.seed_instance(seed)

    def generate(self):
        """Generate random ports.

        Returns
        ----------
        list(int)
            Sorted list of random ports.
        """

        ports = set()

        while len(ports) < self._count:
            ports.add(self._faker.port_number())

        return sorted(ports)
