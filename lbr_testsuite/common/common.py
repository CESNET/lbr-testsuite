"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2020-2021 CESNET, z.s.p.o.

Common function for all components.
"""

import os
import time
from pathlib import Path


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


def compose_output_path(pyt_request, target, suffix="", dir="", directory=""):
    """Compose output path for a file or a directory.

    A path is composed from an optional directory, a target name (or
    path) a test case name and an optional suffix.

    Parameters
    ----------
    pyt_request : FixtureRequest
        Special pytest fixture here used for acccessing test case name.
    target : str or pathlib.Path
        Name of target file or directory.
    suffix : str, optional
        Suffix of the file. Default is empty string (i.e. no suffix).
    dir : str, optional
        DEPRECATED. Path to the directory. Use "directory" instead.
    directory : str, optional
        Path to the directory. Value has higher precedence over "dir"
        parameter (deprecated).

    Returns
    -------
    Path
        Composed path to the object (file or directory).
    """

    if not directory and dir:
        directory = dir

    valid_file_name = pyt_request.node.name.replace("/", "-")
    suffix = f"__{valid_file_name}{suffix}"

    target_path = f"{str(target)}{suffix}"
    return Path(directory) / target_path


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


def get_real_user():
    """Get real user name (even when running under root).

    Returns
    -------
    str
        User name.
    """

    if os.getenv("USER") == "root":
        return os.getenv("SUDO_USER")

    return os.getenv("USER")
