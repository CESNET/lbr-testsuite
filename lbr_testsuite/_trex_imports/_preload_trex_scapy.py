"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Load modules that require TRex version of Scapy.
Modules keep local references to loaded modules.
"""

# isort: off
import lbr_trex_client  # noqa
from trex.stl.api import *  # noqa

# Since we can load packet from packet crafter into
# TRex, we need to make sure PC uses TRex Scapy
# version, otherwise it leads to problems as TRex
# expects modified Scapy objects.
from ..packet_crafter import (  # noqa
    abstract_packet_crafter,
    scapy_packet_crafter,
    trex_packet_crafter,
)
