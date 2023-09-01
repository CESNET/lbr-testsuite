"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Importing certain modules from ``lbr_trex_client`` automatically
imports custom TRex Scapy modules, overriding some existing Scapy imports.
Those modules are older version (2.4.3) and are modified in a certain
way to fit TRex needs. Thus they might not support certain operations
or have bugfixes as the latest, unmodified version of Scapy.

If we need to use standard (local) Scapy modules, we must:
1) Remove current Scapy modules from ``sys.modules`` cache.
2) Remove path to TRex Scapy from ``sys.path``.
3) Remove scapy from __builtins__ module.

Explanation of points 1) and 2):
Otherwise, any Scapy imports would reimport TRex Scapy.
It's because import system first searches sys.modules
cache, then paths in sys.path. Importing ``trex`` module
from ``lbr_trex_client`` modifies sys.path so that
TRex paths to Scapy are found first.

Explanation of point 3):
Scapy version 2.4.3 contains special behaviour, where
importing scapy.all modifies  __builtins__ module and
adds scapy objects to it. "scapy" is then threated as
built-in object such as None, int() or len(). And it points
to itself, not the local Scapy we want. Then we then need to
remove Scapy from __builtins__ module.


Deimporting TRex Scapy does not interfere with TRex modules
that require custom TRex Scapy. Those modules, due to mechanism
described above import TRex Scapy modules and hold local
reference of "scapy" to TRex Scapy module. Thus later changes
to sys.modules, sys.path or __builtins__ do not bother them.

Example of standalone usage::

    # Remove TRex Scapy modules
    _deimport_completely()

    # Import official Scapy module
    from scapy.all import IP
"""

import builtins
import sys


def _deimport_from_sys_modules():
    """Deimport any loaded Scapy modules from sys.modules cache."""

    trex_scapy = []

    for module in sys.modules:
        if module.startswith("scapy"):
            trex_scapy.append(module)

    for module in trex_scapy:
        sys.modules.pop(module)


def _deimport_from_sys_path():
    """Remove path to custom TRex Scapy modules from sys.path."""

    for path in sys.path:
        if "external_libs/scapy" in path:
            sys.path.remove(path)
            break


def _deimport_from_builtins():
    """Remove scapy entry from __builtins__ module."""

    if "scapy" in builtins.__dict__:
        builtins.__delattr__("scapy")


def _deimport_completely():
    """Deimport scapy from all known objects."""

    _deimport_from_sys_modules()
    _deimport_from_sys_path()
    _deimport_from_builtins()
