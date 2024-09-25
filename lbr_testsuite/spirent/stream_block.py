"""
Author(s):
    Kamil Vojanec <vojanec@cesnet.cz>
    Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Stream block helper class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Optional

from .spirent import Spirent


class AbstractStreamBlock(ABC):
    """Abstract class representing a Spirent stream block."""

    def __init__(
        self,
        spirent: Spirent,
        name: str,
    ):
        """
        Parameters
        ----------
        spirent : Spirent
            Instance of Spirent using configuration from this
            stream block object.
        name : str
            Stream block name.
        """

        self._spirent = spirent
        self._stc_handler = spirent._stc_handler
        self._name = name

    def name(self):
        return self._name

    @abstractmethod
    def apply(self):
        """Apply the stream block using instance attributes."""

        pass

    def start(self):
        """Start generating traffic from the stream block."""

        self._stc_handler.stc_start_stream_block(self._name)

    def stop(self):
        """Stop generating traffic from the stream block."""

        self._stc_handler.stc_stop_stream_block(self._name)

    def _read_stats(self, key: str) -> int:
        """Retrieve streamblock stats with given key."""

        sb_handler = self._stc_handler.stc_stream_block(self._name)
        sb_tx = int(self._stc_handler.stc_tx_stream_block_results(sb_handler, key)[0][0])
        sb_rx = int(self._stc_handler.stc_rx_stream_block_results(sb_handler, key)[0][0])

        return (sb_tx, sb_rx)

    def _read_float_rxstats(self, key: str) -> float:
        """Retrieve RX streamblock floating point stats with given key"""

        sb_handler = self._stc_handler.stc_stream_block(self._name)
        sb_stats = float(self._stc_handler.stc_rx_stream_block_results(sb_handler, key)[0][0])

        return sb_stats

    def _is_active(self) -> bool:
        """Check if stream block is active

        This method is considered "protected" and should only be
        used in inherited classes.

        Returns
        -------
        bool
            True if stream block is active, False otherwise.
        """

        sb_handler = self._stc_handler.stc_stream_block(self._name)

        sb_active = self._stc_handler.stc_rx_stream_block_results(sb_handler, "Active")[0][0]
        return sb_active == "true"

    def _apply_active(self, active: bool):
        """Activate stream block.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        active : bool
            Active state of the stream block.
        """

        if active is True:
            sb_active = "TRUE"
        else:
            sb_active = "FALSE"

        sb_handler = self._stc_handler.stc_stream_block(self._name)
        self._stc_handler.stc_attribute(sb_handler, "Active", sb_active)

    def get_tx_rx_stats(self):
        """Retrieve transmitted and received statistics from STC.

        Returns
        -------
        dict
            Dictionary with extracted stats.
        """

        stats = {
            "rx": {},
            "tx": {},
        }

        key = "FrameCount"
        sb_tx, sb_rx = self._read_stats(key)
        stats["tx"][key] = sb_tx
        stats["rx"][key] = sb_rx

        return stats

    def get_latency_stats(self):
        """Retrieve block latency statistics from STC.

        Returns
        -------
        dict
            Dictionary with extracted stats.
        """

        stats = {}

        for key in ["MinLatency", "AvgLatency", "MaxLatency"]:
            sb_lat = self._read_float_rxstats(key)
            stats[key] = sb_lat

        return stats

    def get_jitter_stats(self):
        """Retrieve jitter statistics from STC.

        Returns
        -------
        dict
            Dictionary with extracted stats.
        """

        if not self._stc_handler.stc_check_result_view_mode("LATENCY_JITTER"):
            raise RuntimeError("Jitter statistics are only available in latency-jitter mode.")

        jitter_counters = [
            ("AvgJitter", float),
            ("MaxJitter", float),
            ("MinJitter", float),
            ("Rfc4689AbsoluteAvgJitter", float),
            ("TotalJitter", float),
        ]

        stats = {}

        for key, val_type in jitter_counters:
            val = self._stc_handler.stc_filtered_stream_results(key, self._name)[0][0][0]
            if val == "N/A":
                stats[key] = None
            else:
                stats[key] = val_type(val)

        return stats

    def _apply_load_megabits(self, megabits: int):
        """Set stream blocks load in STC.

        Current implementation is limited to MEGABITS_PER_SECOND only.
        This unit has to be set in STC stream block configuration.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        megabits : int
            Load value.
        """

        sb_load_unit = self._stc_handler.stc_get_stream_block_load_unit(self._name)
        assert (
            sb_load_unit == "MEGABITS_PER_SECOND"
        ), f"Stream block load unit is not set ({sb_load_unit}) as expected (MEGABITS_PER_SECOND)."

        self._stc_handler.stc_set_stream_block_load(self._name, str(megabits))

    def _apply_packet_len_bytes(self, packet_len: int):
        """Set stream block packet length in bytes.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        packet_len : int
            Requested packet length.
        """

        self._spirent.set_stream_blocks_packet_length(self._name, packet_len)

    def _apply_src_mac(self, mac_address: str):
        """Set stream block's source MAC address.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        mac_address : str
            Requested source MAC address.
        """

        self._spirent.set_stream_blocks_src_mac(self._name, mac_address)

    def _apply_dst_mac(self, mac_address: str):
        """Set stream block's destination MAC address.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        mac_address : str
            Requested destination MAC address.
        """

        self._spirent.set_stream_blocks_dst_mac(self._name, mac_address)

    def _apply_vlan(self, vlan: int):
        """Set stream block's VLAN.

        This method is considered "protected" and should only be
        used in inherited classes.

        Parameters
        ----------
        vlan : int
            Requested VLAN to be set. If set to 0,
            the VLAN will be deleted.
        """

        if vlan != 0:
            self._spirent.set_stream_blocks_vlan(self._name, vlan)
        else:
            self._spirent.delete_stream_blocks_vlan(self._name)


class StreamBlock(AbstractStreamBlock):
    """Stream block class that can be dynamically configured through the
    provided set_*() methods. The changes are not applied immediately.
    To apply staged changes, use the 'apply()' method.
    """

    @dataclass
    class Config:
        """Dynamic stream block configuration. Properties of this object
        represent values that can be modified during runtime. However,
        the properties may not be applied instantly. Instead, the 'apply()'
        method should be used to apply the dynamic configuration in inherited
        classes.
        """

        active: bool = None
        packet_len: int = None
        src_mac: Optional[str] = None
        dst_mac: Optional[str] = None
        vlan: int = None

    def __init__(
        self,
        spirent: Spirent,
        name: str,
        **kwargs: dict,
    ):
        """Initialize an instance of StreamBlock.

        Parameters
        ----------
        spirent : Spirent
            Instance of Spirent using configuration from this
            stream block object.
        name : str
            Stream block name.
        kwargs : dict
            Dictionary with additional arguments.
            The available arguments may also be set by their
            corresponding setter methods.
        """

        if "src_mac" not in kwargs:
            kwargs["src_mac"] = spirent.determine_src_mac_address()

        super().__init__(spirent, name)
        self._applied_config = self.Config()  # Applied config is empyty
        self._working_config = self.Config(**kwargs)

    def set_active(self, active: bool):
        """Set stream block's active state."""

        self._working_config.active = active

    def set_packet_len(self, packet_len: int):
        """Set stream block's packet length.

        Parameters
        ----------
        packet_len : int
            Requested packet length.
        """

        self._working_config.packet_len = packet_len

    def set_src_mac(self, src_mac: str):
        """Set stream block's source MAC address.

        Parameters
        ----------
        src_mac : str
            Requested source MAC address.
        """

        self._working_config.src_mac = src_mac

    def set_dst_mac(self, dst_mac: str):
        """Set stream block's destination MAC address.

        Parameters
        ----------
        dst_mac : str
            Requested destination MAC address.
        """

        self._working_config.dst_mac = dst_mac

    def set_vlan(self, vlan: int):
        """Set stream block's VLAN.

        Parameters
        ----------
        vlan : int
            Requested VLAN.
        """

        self._working_config.vlan = vlan

    def apply(self):
        """Apply the working configuration.

        This method should also be called by the 'apply()'
        method in inherited classes. To be used correctly, it
        should be called after all configuration of the inherited
        classes is done.
        """

        if self._working_config.packet_len != self._applied_config.packet_len:
            self._apply_packet_len_bytes(self._working_config.packet_len)

        if self._working_config.active != self._applied_config.active:
            self._apply_active(self._working_config.active)

        if self._working_config.vlan != self._applied_config.vlan:
            self._apply_vlan(self._working_config.vlan)

        if self._working_config.src_mac != self._applied_config.src_mac:
            self._apply_src_mac(self._working_config.src_mac)

        if self._working_config.dst_mac != self._applied_config.dst_mac:
            self._apply_dst_mac(self._working_config.dst_mac)

        self._applied_config = replace(self._working_config)
