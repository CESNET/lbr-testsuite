"""
Author(s):
    Dominik Tran <tran@cesnet.cz>
    Jan Viktorin <viktorin@cesnet.cz>
    Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2022-2024 CESNET, z.s.p.o.

Random types for L3 and L4 headers, IP address and ports.
"""

import faker
import scapy.all as scapy
import scapy.contrib.igmp as igmp


class RandomType:
    """Base class for all random types.
    This class initializes the faker random
    generator and optionally seeds it.
    """

    def __init__(self, seed=None):
        """
        Parameters
        ----------
        seed : int
            Seed to be used for faker random generator.
        """

        self._faker = faker.Faker()
        if seed is not None:
            self._faker.seed_instance(seed)


class RandomIP(RandomType):
    """Class for generating random IP addresses.

    Parameters
    ----------
    count : int, optional
        Count of IP adresses to generate.
    seed : int, optional
        Seed value for pseudo-random generator.
    """

    def __init__(self, count=1, seed=None):
        super().__init__(seed)
        self._count = count

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


class RandomPort(RandomType):
    """Class for generating random ports.

    Parameters
    ----------
    count : int, optional
        Count of ports to generate.
    seed : int, optional
        Seed value for pseudo-random generator.
    """

    def __init__(self, count=1, seed=None):
        super().__init__(seed)
        self._count = count

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


class RandomHeader(RandomType):
    """Base class for all random L3 and L4 headers."""

    @staticmethod
    def update_header_fields(hdr: scapy.Packet, fields: dict) -> scapy.Packet:
        """Modify provided scapy packet header with fields provided
        in a dictionary. Fields not present in the dictionary are
        not modified in the packet.

        Parameters
        ----------
        hdr : scapy.Packet
            Original scapy packet header.
        fields : dict
            Dictionary with other header fields to be set.

        Returns
        -------
        scapy.Packet
            Modified scapy packet header.
        """

        for field, val in fields.items():
            hdr.__setattr__(field, val)

        return hdr


class RandomIPv4Header(RandomHeader):
    def __call__(self, **kwargs) -> scapy.IP:
        """Generate a random IPv4 header.
        The following header fields are randomized:

        tos : Type of Service
        id : Identification
        ttl : Time to Live
        src : Source Address
        dst : Destination Address

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.IP
            constructor.

        Returns
        -------
        scapy.IP
            Randomized IPv4 packet.
        """

        hdr = scapy.IP(
            tos=self._faker.random_int(min=0, max=(2**8) - 1),
            id=self._faker.random_int(min=0, max=(2**16) - 1),
            ttl=self._faker.random_int(min=1, max=(2**8) - 1),
            src=self._faker.ipv4(),
            dst=self._faker.ipv4(),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomIPv6Header(RandomHeader):
    def __call__(self, **kwargs) -> scapy.IPv6:
        """Generate a random IPv6 header.
        The following header fields are randomized:

        tc : Traffic Class
        fl : Flow Label
        hlim : Hop Limit
        src : Source Address
        dst : Destination Address

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.IPv6
            constructor.

        Returns
        -------
        scapy.IPv6
            Randomized IPv6 packet.
        """

        hdr = scapy.IPv6(
            tc=self._faker.random_int(min=0, max=(2**8) - 1),
            fl=self._faker.random_int(min=0, max=(2**20) - 1),
            hlim=self._faker.random_int(min=1, max=(2**8) - 1),
            src=self._faker.ipv6(),
            dst=self._faker.ipv6(),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomTCPHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.TCP:
        """Generate a random TCP header.
        The following header fields are randomized:

        sport : Source Port
        dport : Destination Port
        seq : Sequence Number
        ack : Acknowledge Number
        flags : Flags
        window : Window Size
        urgptr : Urgent Pointer

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.TCP
            constructor.

        Returns
        -------
        scapy.TCP
            Randomized TCP packet.
        """

        hdr = scapy.TCP(
            sport=self._faker.random_int(min=0, max=(2**16) - 1),
            dport=self._faker.random_int(min=0, max=(2**16) - 1),
            seq=self._faker.random_int(min=0, max=(2**32) - 1),
            ack=self._faker.random_int(min=0, max=(2**32) - 1),
            flags=self._faker.random_int(min=0, max=(2**8) - 1),
            window=self._faker.random_int(min=0, max=(2**16) - 1),
            urgptr=self._faker.random_int(min=0, max=(2**16) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomUDPHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.UDP:
        """Generate a random UDP header.
        The following header fields are randomized:

        sport : Source Port
        dport : Destination Port

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.UDP
            constructor.

        Returns
        -------
        scapy.UDP
            Randomized UDP packet.
        """

        hdr = scapy.UDP(
            sport=self._faker.random_int(min=0, max=(2**16) - 1),
            dport=self._faker.random_int(min=0, max=(2**16) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomSCTPHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.SCTP:
        """Generate a random SCTP header.
        The following header fields are randomized:

        sport : Source Port
        dport : Destination Port
        tag : Verification Tag

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.SCTP
            constructor.

        Returns
        -------
        scapy.SCTP
            Randomized SCTP packet.
        """

        hdr = scapy.SCTP(
            sport=self._faker.random_int(min=0, max=(2**16) - 1),
            dport=self._faker.random_int(min=0, max=(2**16) - 1),
            tag=self._faker.random_int(min=0, max=(2**32) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomNDPHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.ICMPv6ND_NS:
        """Generate a random IPv6 NDP header.
        The following header fields are randomized:

        code : Code

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.ICMPv6ND_NS
            constructor.

        Returns
        -------
        scapy.ICMPv6ND_NS
            Randomized NDP packet.
        """

        hdr = scapy.ICMPv6ND_NS(
            code=self._faker.random_int(min=0, max=(2**8) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomICMPHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.ICMP:
        """Generate a random ICMP header.
        The following header fields are randomized:

        code : Code

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.ICMP
            constructor.

        Returns
        -------
        scapy.ICMP
            Randomized ICMP packet.
        """

        hdr = scapy.ICMP(
            code=self._faker.random_int(min=0, max=(2**8) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomICMPv6Header(RandomHeader):
    def __call__(self, **kwargs) -> scapy.ICMPv6EchoRequest:
        """Generate a random ICMPV6 header.
        The following header fields are randomized:

        code : Code
        id : Identification
        seq : Sequence Number

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.ICMPv6EchoRequest
            constructor.

        Returns
        -------
        scapy.ICMPv6EchoRequest
            Randomized ICMPv6 packet.
        """

        hdr = scapy.ICMPv6EchoRequest(
            code=self._faker.random_int(min=0, max=(2**8) - 1),
            id=self._faker.random_int(min=0, max=(2**16) - 1),
            seq=self._faker.random_int(min=0, max=(2**16) - 1),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomIGMPHeader(RandomHeader):
    def __call__(self, **kwargs) -> igmp.IGMP:
        """Generate a random IGMP header.
        The following header fields are randomized:

        mrcode : Type
        gaddr : Group Address

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.IGMP
            constructor.

        Returns
        -------
        scapy.IGMP
            Randomized IGMP packet.
        """

        hdr = igmp.IGMP(
            mrcode=self._faker.random_int(min=0, max=(2**8) - 1),
            gaddr=self._faker.ipv4(),
        )
        return self.update_header_fields(hdr, kwargs)


class RandomMLDHeader(RandomHeader):
    def __call__(self, **kwargs) -> scapy.ICMPv6MLQuery:
        """Generate a random ICMPv6 MLD header.
        The following header fields are randomized:

        code : Code
        mrd : Maximum Response Delay
        mladdr : Multicast Address

        Note
        ----
        Other header fields are not randomized in order
        to keep packet's validity.

        Parameters
        ----------
        **kwargs : dict
            Other keyword arguments passed to scapy.ICMPv6MLQuery
            constructor.

        Returns
        -------
        scapy.ICMPv6MLQuery
            Randomized MLD packet.
        """

        hdr = scapy.ICMPv6MLQuery(
            code=self._faker.random_int(min=0, max=(2**8) - 1),
            mrd=self._faker.random_int(min=0, max=(2**16) - 1),
            mladdr=self._faker.ipv6(),
        )
        return self.update_header_fields(hdr, kwargs)
