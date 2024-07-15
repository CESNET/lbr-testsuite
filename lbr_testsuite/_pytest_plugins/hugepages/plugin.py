"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Pytest plugin with hugepage fixtures.
"""

import functools
import os
import shutil
from pathlib import Path

from pytest_cases import fixture

from lbr_testsuite.common.conv import UnitsPolicy, parse_size
from lbr_testsuite.dpdk_application.hugepages import (
    clear_hugepages,
    configure_hugepages,
)


def pytest_addoption(parser):
    parser.addoption(
        "--hugepages-setup",
        metavar="setup",
        type=str,
        default="8G",
        help=(
            "Size of hugepages to prealloc. Size is in bytes with K, M, or G suffix. "
            "(Default 8G)"
        ),
    )
    parser.addoption(
        "--hugepages-size",
        metavar="size",
        type=str,
        default="1G",
        help=(
            "Size of one hugepage, see contents of /sys/kernel/mm/hugepages. "
            "Size is in bytes with K, M, or G suffix. (Default 1G)"
        ),
    )
    parser.addoption(
        "--hugepages-cleanup",
        default=False,
        action="store_true",
        help=(
            "Free allocated hugepages when tests are done. Repeated allocation and de-allocation"
            "of hugepages might lead to allocation failures. (Default False)"
        ),
    )
    parser.addoption(
        "--hugepages-mount-dir",
        metavar="mount-dir",
        type=str,
        default="/mnt/huge",
        help="Hugepages mountpoint. (Default /mnt/huge)",
    )


@fixture(scope="session")
def hugepages_mountpoint_dir(request, require_root):
    """Create mounpoint directory for hugepages.

    Pytest request fixture is used here to access command line
    arguments.

    Parameters
    ----------
    request : fixture, pytest.FixtureRequest
        Special pytest fixture, here used to access command line parameters.
    require_root : fixture, None
        This fixture requires root.

    Returns
    -------
    Path
        Path to the created mountpoint.
    """

    mount_dir = request.config.getoption("hugepages_mount_dir")
    os.makedirs(mount_dir, exist_ok=True)
    yield Path(mount_dir).resolve()

    if request.config.getoption("hugepages_cleanup"):
        shutil.rmtree(mount_dir)


@fixture(scope="session")
def hugepages(request, require_root, hugepages_mountpoint_dir):
    """Allocate hugepages for DPDK applications. By default,
    this fixture does not clear allocated hugepages. This
    behaviour is controlled by '--hugepages-cleanup' commandline
    parameter.

    Parameters
    ----------
    request : fixture, pytest.FixtureRequest
        Special pytest fixture, here used to access command line parameters.
    require_root : fixture, None
        This fixture requires root.
    hugepages_mountpoint_dir : fixture, Path
        Path to the hugepage mountpoint directory.

    Returns
    -------
    int
        Size of allocated hugepages in bytes.
    """

    size = request.config.getoption("hugepages_setup")
    pagesize = request.config.getoption("hugepages_size")

    if request.config.getoption("hugepages_cleanup"):
        fin = functools.partial(clear_hugepages, hugepages_mountpoint_dir)
        request.addfinalizer(fin)

    configure_hugepages(size, pagesize, hugepages_mountpoint_dir)

    return parse_size(size, units=UnitsPolicy.IEC)
