"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Module for managing a spirent Device component.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from .spirent import Spirent


class AbstractDevice(ABC):
    """Abstract class representing a spirent device."""

    def __init__(
        self,
        spirent: Spirent,
        name: str,
    ):
        """
        Parameters
        ----------
        spirent : Spirent
            Instance of Spirent that will be configured.
        name : str
            Device name.
        """

        self._spirent = spirent
        self._name = name

    def name(self):
        return self._name

    @abstractmethod
    def apply(self):
        """Apply the device configuration to spirent."""

        pass

    def _apply_vlan(self, vlan: int):
        """Set device's VLAN.

        This method is considered "protected" and should only
        be used in inherited classes.

        Parameters
        ----------
        vlan : int
            Requested VLAN to be set. If set to 0, the device
            VLAN is deleted.
        """

        if vlan != 0:
            self._spirent.set_device_vlan(self._name, vlan)
        else:
            self._spirent.delete_device_vlan(self._name)

    def _apply_mac(self, mac: str):
        """Set device's MAC address.

        Parameters
        ----------
        mac : str
            Requested MAC address to be set on Spirent.
        """

        self._spirent.set_device_mac(self._name, mac)

    def _resolve_neighbours(self):
        """Perform a neighbour resolution using spirent device."""

        self._spirent._stc_handler.stc_start_arpnd()


class Device(AbstractDevice):
    """Device class that can be dynamically configured using the provided
    set_*() methods. The changes are not applied immediately.
    To apply staged changes, use the 'apply()' method.
    """

    @dataclass
    class Config:
        """Dynamic device configuration. Properties of this object
        represent values that can be modified during runtime. However,
        the properties are only applied whenever the 'apply()' method is
        called.
        """

        mac: str = None
        vlan: int = None

    def __init__(
        self,
        spirent: Spirent,
        name: str,
        **kwargs: dict,
    ):
        """
        Parameters
        ----------
        spirent : Spirent
            Instance of Spirent object that will be configured.
        name : str
            Device name.
        kwargs : dict
            Dictionary with additional arguments.
            The available arguments may also be set with their
            corresponding setter methods.
        """

        if "mac" not in kwargs:
            kwargs["mac"] = spirent.determine_src_mac_address()

        super().__init__(spirent, name)

        self._applied_config = self.Config()
        self._working_config = self.Config(**kwargs)

    def set_vlan(self, vlan: int):
        """Set the requested VLAN.

        Parameters
        ----------
        vlan : int
            Requested VLAN.
        """

        self._working_config.vlan = vlan

    def set_mac(self, mac: str):
        """Set the device's MAC address

        Parameters
        ----------
        mac : str
            Requested MAC address.
        """

        self._working_config.mac = mac

    def apply(self):
        """Apply the working configuration"""

        if self._working_config.mac != self._applied_config.mac:
            self._apply_mac(self._working_config.mac)

        if self._working_config.vlan != self._applied_config.vlan:
            self._apply_vlan(self._working_config.vlan)

        self._applied_config = replace(self._working_config)

    def resolve_neighbours(self):
        """Perform neighbour resolution using the spirent device"""

        self._resolve_neighbours()
