"""
Author(s): Jakub Šuráň <xsuran07@fit.vutbr.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Pytest plugin with common fixtures.
"""

import os

import pytest
from pytest_cases import fixture


@fixture(scope="session")
def require_root():
    """Fixture checking whether a test is running under the root."""

    euid = os.geteuid()

    if euid != 0:
        pytest.skip(f"insufficient permissions, euid: {euid}")
