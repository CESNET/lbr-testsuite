# isort: off
import sys
from ._trex_imports import _deimport_scapy as ds
from ._trex_imports import _deimport_yaml as dy

if "scapy" in sys.modules:
    # If Scapy was imported before lbr_testsuite, deimport
    # it as TRex deimport mechanism isn't good enough
    ds._deimport_from_sys_modules()
    ds._deimport_from_builtins()

# Preload TRex Scapy into TRex modules
from ._trex_imports import _preload_trex_scapy  # noqa

# Remove TRex Scapy completely
ds._deimport_completely()

# isort: on

from . import data_table  # noqa
from . import dpdk_application  # noqa
from . import executable  # noqa
from . import ipconfigurer  # noqa
from . import packet_crafter  # noqa
from . import profiling  # noqa
from . import spirent  # noqa
from . import throughput_runner  # noqa
from . import topology  # noqa
from . import trex  # noqa
from .common import *  # noqa


dy._deimport_completely()
