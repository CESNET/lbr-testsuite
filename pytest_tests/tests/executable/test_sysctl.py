"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of sysctl module.
"""

import pytest

from lbr_testsuite.common import sysctl


TEST_VAR = "net.ipv6.conf.default.disable_ipv6"
EXPECTED_INIT_VALUE = "1"


def _flip_value(value):
    v = int(value)
    assert v in [0, 1], "value has to be 0 or 1"

    return str(1 - v)


def _sysctl_get_value(var):
    curr_value = sysctl.sysctl_get(var)
    return curr_value[0]


def test_sysctl_set_get(require_root, testing_namespace):
    """Test capability of setting kernel variable."""

    init_value = _sysctl_get_value(TEST_VAR)
    assert init_value == EXPECTED_INIT_VALUE, f"Unexpected initial value of {TEST_VAR}."

    set_value = _flip_value(init_value)
    vars_set = sysctl.sysctl_set(TEST_VAR, set_value)
    assert vars_set == 1, "Expected to set exactly one variable"
    curr_value = _sysctl_get_value(TEST_VAR)
    assert curr_value == set_value, f"Unexpected value of {TEST_VAR} after set."

    # cleanup
    vars_set = sysctl.sysctl_set(TEST_VAR, init_value)
    assert vars_set == 1, "Expected to set exactly one variable"
    curr_value = _sysctl_get_value(TEST_VAR)
    assert curr_value == EXPECTED_INIT_VALUE, f"Restoration of original value of {TEST_VAR} failed."


def test_sysctl_set_with_restore(request, require_root, testing_namespace):
    """Test capability of setting kernel variable with automatic
    restoration.
    """

    init_value = _sysctl_get_value(TEST_VAR)
    assert init_value == EXPECTED_INIT_VALUE, f"Unexpected initial value of {TEST_VAR}."

    def verify_restoration_after_cleanup():
        restored = _sysctl_get_value(TEST_VAR)
        assert restored == EXPECTED_INIT_VALUE, f"Restoration of {TEST_VAR} variable failed."

    request.addfinalizer(verify_restoration_after_cleanup)

    set_value = _flip_value(EXPECTED_INIT_VALUE)
    sysctl.sysctl_set_with_restore(request, TEST_VAR, set_value)
    curr_value = _sysctl_get_value(TEST_VAR)
    assert curr_value == set_value, f"Unexpected value of {TEST_VAR} after set."
