from ..._trex_imports.__init__ import TREX_CLIENT
from . import _spirent, _spirent_with_loopback, _virtual_devices, _wired_loopback


if TREX_CLIENT:
    from . import _trex


_wired_loopback._init()
_virtual_devices._init()
_spirent._init()
_spirent_with_loopback._init()
if TREX_CLIENT:
    _trex._init()
