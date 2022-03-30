"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Class representation of PCI address.
"""

import re


class PciAddress:
    """Representation of PCI address.

    Attributes
    ----------
    domain : int
        PCI address domain.
    bus : int
        PCI address bus.
    devid : int
        PCI address device id.
    function : int
        PCI address function.
    """

    def __init__(self, domain=0, bus=0, devid=0, function=0):
        """PCI address object.

        Parameters
        ----------
        domain : int, optional
            PCI address domain
        bus : int, optional
            PCI address bus
        devid : int, optional
            PCI address device id
        function : int, optional
            PCI address function
        """

        self.domain = domain
        self.bus = bus
        self.devid = devid
        self.function = function

    @classmethod
    def _parse(cls, address):
        regexp = r"([0-9a-fA-F]{4}):([0-9a-fA-F]{2}):([0-9a-fA-F]{2}).([0-9a-fA-F]{1})"
        return re.match(regexp, address)

    @classmethod
    def from_string(cls, address):
        """Initialize PciAddress from a string."""

        match = cls._parse(address)
        if not match:
            raise RuntimeError("Not a valid PCI address ({address})")

        groups = [int(x, 16) for x in match.groups()]
        return cls(*groups)

    @classmethod
    def is_valid(cls, address):
        """Check if passed string is a valid PCI address.

        Parameters
        ----------
        address : str
            Input to validate.

        Returns
        -------
        bool
            True if valid PCIe address, False otherwise.
        """

        return cls._parse(address) is not None

    def __str__(self):
        """Convert PciAddress to string."""

        return f"{self.domain:04x}:{self.bus:02x}:{self.devid:02x}.{self.function:x}"
