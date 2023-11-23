"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Deimport TRex yaml module so user can import local yaml module.
For details see "_deimport_scapy.py" file.
"""

import sys


def _deimport_from_sys_modules():
    """Deimport any loaded Yaml modules from sys.modules cache."""

    trex_yaml = []

    for module in sys.modules:
        if module.startswith("yaml"):
            trex_yaml.append(module)

    for module in trex_yaml:
        sys.modules.pop(module)


def _deimport_from_sys_path():
    """Remove path to custom TRex Yaml modules from sys.path."""

    for path in sys.path:
        if "external_libs/pyyaml" in path:
            sys.path.remove(path)
            break


def _deimport_completely():
    """Deimport yaml from all known objects."""

    _deimport_from_sys_modules()
    _deimport_from_sys_path()
