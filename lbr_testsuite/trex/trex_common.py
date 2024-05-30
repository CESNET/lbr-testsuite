"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

File implements common TRex functions or utilities.
"""

import lbr_trex_client  # noqa: F401
from trex.utils.parsing_opts import decode_multiplier


def parse_bandwidth(unit):
    """Convert bandwidth units to float.

    Examples:
        -  "10mbps" converts to 10000000.0
        -  "94kpps" converts to 94000.0
        -  "10.67 Gbps" converts to 10670000000.0
        -  "10 PPS" converts to 10.0

    Parameters
    ----------
    unit : str
        String to be converted into float.
        String can contain spaces and capital letters (like "10 Mpps").

    Returns
    -------
    float
        Converted value.
    """

    unit = unit.lower()
    unit = unit.replace(" ", "")
    return decode_multiplier(unit)["value"]
