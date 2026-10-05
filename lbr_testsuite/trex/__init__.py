from .._trex_imports.__init__ import TREX_CLIENT


if not TREX_CLIENT:
    raise ImportError(
        "Missing dependencies for TRex client, please install using lbr-testsuite[trex]."
    )


from .trex_common import parse_bandwidth  # noqa: E402
from .trex_generator import TRexMachinesPool  # noqa: E402
from .trex_legacy_stateful import TRexLegacyStateful  # noqa: E402
from .trex_manager import TRexManager  # noqa: E402
from .trex_stateful import (  # noqa: E402
    TRexAdvancedStateful,
    TRexProfile,
    TRexProfilePcap,
)
from .trex_stateless import (  # noqa: E402
    TRexStateless,
    TRexStream,
    TRexStreamModeSelector,
)


__all__ = [
    "TRexMachinesPool",
    "TRexStreamModeSelector",
    "TRexStream",
    "TRexStateless",
    "TRexProfile",
    "TRexAdvancedStateful",
    "TRexManager",
    "TRexProfilePcap",
    "parse_bandwidth",
    "TRexLegacyStateful",
]
