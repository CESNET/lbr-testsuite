"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2021 CESNET, z.s.p.o.

Common function for all components.
"""

from pathlib import Path
import re
import time

from ..executable import executable


def sysctl_set(variables, values):
    """Set kernel variable(s) using sysctl tool.

    Parameters
    ----------
    variables : list(str) or str
        List of variables names.
    values : list(str) or str
        List of variables values.
    """

    if type(variables) is str:
        variables = [variables]
    if type(values) is str:
        values = [values]

    assert len(variables) == len(values)

    for var, val in zip(variables, values):
        executable.Tool(['sysctl', '-w', f'{var}={val}']).run()


def sysctl_get(variables):
    """Get kernel variable(s) using sysctl tool.

    Parameters
    ----------
    variables : list(str) or str
        List of variables names.

    Returns
    -------
    list or str
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
        var_re = var.replace('.', '\\.')
        var_re = rf'^{var_re}\s*=\s*([0-9])+$'

        stdout, _ = executable.Tool(['sysctl', var]).run()

        match = re.match(var_re, stdout)
        if not match:
            raise RuntimeError(f'Unable to match {var} kernel variable.')
        values.append(match[1])

    return values


def sysctl_set_with_restore(pyt_request, variables, values):
    """Set kernel variable(s) using sysctl tool with restoration of
    original values.

    Current value(s) of variables are retrieved, stored and in the
    cleanup phase restored.

    Parameters
    ----------
    pyt_request : FixtureRequest
        Special pytest fixture, here used for adding of a finalizer.
    variables : list(str)
        List of variables names.
    values : list(str)
        List of variables values.
    """

    original_values = sysctl_get(variables)

    sysctl_set(variables, values)

    def restore_original_values():
        """ Cleanup function for restoring of original variables values.
        """

        sysctl_set(variables, original_values)
    pyt_request.addfinalizer(restore_original_values)


def wait_until_condition(condition, timeout=1.0, sleep_step=1):
    """Wait until a condition become true.

    Parameters
    ----------
    condition : callable
        Condition to wait for.
    timeout : float, optional
        Maximal time (seconds) to wait for the the condition.
    sleep_step : float, optional

    Returns
    -------
    bool
        True if the condition become true, False if the timeout expires.
    """

    now = started = time.monotonic()

    while True:
        if condition():
            return True

        if now - started > timeout:
            return False

        time.sleep(sleep_step)
        now = time.monotonic()


dcpro_tmp_dir_global = None


def compose_output_path(pyt_request, target, suffix=''):
    """Compose output path in tests temporary directory for a file or
    a directory.

    A path is composed from the tests tmp directory, a target name (or
    path) a test case name and a suffix.

    Parameters
    ----------
    pyt_request : FixtureRequest
        Special pytest fixture here used for acccessing test case name.
    target : str
        Name of target file or directory.
    suffix : str, optional
        Suffix of the file. Default is empty string (i.e. no suffix).

    Returns
    -------
    Path
        Composed path to the object (file or directory).
    """

    global dcpro_tmp_dir_global
    if not dcpro_tmp_dir_global:
        raise Exception('Temporary directory is not set.')

    valid_file_name = pyt_request.node.name.replace('/', '-')
    suffix = f'__{valid_file_name}{suffix}'

    target_path = f'{target}{suffix}'
    return Path(dcpro_tmp_dir_global) / target_path


def local_tests(items, config, testdir):
    """Generator of tests belonging to testdir directory from list of
    tests.

    Parameters
    ----------
    items : list(pytest.Item)
        List of test item objects.
    config: _pytest.config.Config
        Pytest config object.
    testdir : pathlib.Path
        Absolute path to test's directory.

    Returns
    -------
    pytest.Item
        Returns test items from the test directory.
    """

    rootdir = config.rootpath
    testdir = testdir.relative_to(rootdir)

    for item in items:
        # nodeid contains name and relative path to a test case
        if item.nodeid.startswith(str(testdir)):
            yield item


def case_name_contains(item, name_parts):
    """Check whether test case name contains all required parts.

    Parameters
    ----------
    items : list(pytest.Item)
        List of test item objects.
    name_parts : list(str)
        List of strings which test name has to contain.

    Returns
    -------
    Bool
        True when all required name parts are contained within a test
        name, False otherwise.
    """

    for name_part in name_parts:
        if name_part not in item.name:
            return False
    return True
