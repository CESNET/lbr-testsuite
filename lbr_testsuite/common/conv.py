"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Common conversion functions.
"""

import re
from enum import StrEnum


"""
Extra bytes added to L2 packet size when converting:
7B preamble + 1B SoF + 12B minimal IFG.
"""
PACKET_EXTRA_BYTES = 20


def mbps_to_mpps(thrpt_mbps: float, pkt_len: int):
    """Convert megabits per second throughput into megapackets per second.

    Parameters
    ----------
    thrpt_mbps : float
        Throughput value in megabits per second (on L1).
    pkt_len : int
        Individual packet length in bytes (on L2 without FCS).

    Returns
    -------
    float
        Throughput value in megapackets per second.
    """

    return thrpt_mbps / ((pkt_len + PACKET_EXTRA_BYTES) * 8)


def mpps_to_mbps(thrpt_mpps: float, pkt_len: int):
    """Convert megapackets per second throughput into megabits per second.

    Parameters
    ----------
    thrpt_mpps : float
        Throughput value in megapackets per second.
    pkt_len : int
        Individual packet length in bytes (on L2 without FCS).

    Returns
    -------
    float
        Throughput value in megabits per second (on L1).
    """

    return thrpt_mpps * ((pkt_len + PACKET_EXTRA_BYTES) * 8)


class UnitsPolicy(StrEnum):
    """Units policy to be used in size conversion.
    Used to avoid confusion when comparing decimal and binary
    size values.
    """

    """SI defines base 10 prefixes for conversion.
    See: https://en.wikipedia.org/wiki/Metric_prefix#List_of_SI_prefixes
    """
    SI = "si"

    """IEC Defines binary prefixes for conversion.
    See: https://en.wikipedia.org/wiki/Binary_prefix#Prefixes
    """
    IEC = "iec"


def parse_size(
    size_str: str,
    units: UnitsPolicy = UnitsPolicy.SI,
) -> int:
    """Parse size - value with k, M, G suffix into
    an integer representing the size in bytes.

    Parameters
    ----------
    size_str : str
        Size string to be parsed. Contains a value
        with a unit (k, M, G, T).
    units : UnitsPolicy
        Specify the unit used for conversion.

    Returns
    -------
    int
        Integer size in bytes.
    """

    # First match group matches the value.
    # Second match group matches the unit.
    reg = r"(\d+)\s*([kMGT])"
    match = re.match(reg, size_str).groups()

    assert len(match) == 2, "Must match only the value and unit"

    mult_table = {
        UnitsPolicy.SI: {
            "k": 1e3,
            "M": 1e6,
            "G": 1e9,
            "T": 1e12,
        },
        UnitsPolicy.IEC: {
            "k": 2**10,
            "M": 2**20,
            "G": 2**30,
            "T": 2**40,
        },
    }

    val = int(match[0])
    mult = mult_table[units][match[1]]
    return val * mult
