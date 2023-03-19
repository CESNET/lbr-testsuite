"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Functions for manipulation with kernel variables.
"""

import re

from ..executable import executable


def sysctl_set(variables, values, netns=None):
    """Set kernel variable(s) using sysctl tool.

    Parameters
    ----------
    variables : list(str) or str
        List of variables names.
    values : list(str) or str
        List of variables values.
    netns : str, optional
        Network namespace name. If set, a command is executed in
        a namespace using the "ip netns" command. Default "None".
    """

    if type(variables) is str:
        variables = [variables]
    if type(values) is str:
        values = [values]

    assert len(variables) == len(values)

    for var, val in zip(variables, values):
        cmd = executable.Tool(["sysctl", "-w", f"{var}={val}"], netns=netns)
        cmd.run()


def sysctl_get(variables, netns=None):
    """Get kernel variable(s) using sysctl tool.

    Parameters
    ----------
    variables : list(str) or str
        List of variables names.
    netns : str, optional
        Network namespace name. If set, a command is executed in
        a namespace using the "ip netns" command. Default "None".

    Returns
    -------
    list(str)
        List of variables values.

    Raises
    ------
    RuntimeError
        If variable has not been matched.
    """

    if type(variables) is str:
        variables = [variables]

    values = []

    for var in variables:
        var_re = var.replace(".", "\\.")
        var_re = rf"^{var_re}\s*=\s*([0-9])+$"

        cmd = executable.Tool(["sysctl", var], netns=netns)
        stdout, _ = cmd.run()

        match = re.match(var_re, stdout)
        if not match:
            raise RuntimeError(f"Unable to match {var} kernel variable.")
        values.append(match[1])

    return values


def sysctl_set_with_restore(pyt_request, variables, values, netns=None):
    """Set kernel variable(s) using sysctl tool with restoration of
    original values.

    Current value(s) of variables are retrieved, stored and in the
    cleanup phase restored.

    Parameters
        pyt_request : FixtureRequest
        Special pytest fixture, here used for adding of a finalizer.
    variables : list(str) or str
        List of variables names.
    values : list(str) or str
        List of variables values.
    netns : str, optional
        Network namespace name. If set, a command is executed in
        a namespace using the "ip netns" command. Default "None".
        Note: As in most cases a network namespace is deleted upon
        a test cleanup, restoration of sysctl option within a namespace
        does not make much sense.
    """

    original_values = sysctl_get(variables, netns)

    def restore_original_values():
        """Cleanup function for restoring of original variables values."""

        sysctl_set(variables, original_values, netns)

    pyt_request.addfinalizer(restore_original_values)

    sysctl_set(variables, values, netns)
