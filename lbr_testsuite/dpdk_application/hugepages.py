"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Hugepage configuration module.
"""

from pathlib import Path
from typing import Union

from lbr_testsuite import executable


def configure_hugepages(
    huge_alloc: str = "8G",
    huge_pagesize: str = "1G",
    huge_dir: Union[str, Path] = Path("/mnt/huge"),
):
    """Configure hugepages using dpdk-hugepages tool.

    Parameters
    ----------
    huge_alloc : str
        Hugepages to allocate. String contains a numeric value with
        K, M or G suffix.
    huge_pagesize : str
        Size of a single hugepage. String contains a numeric value
        with K, M or G suffix.
    huge_dir : str or Path.
        Path to the hugepage mountpoint directory.
    """

    executable.Tool(
        [
            "dpdk-hugepages",
            "--setup",
            huge_alloc,
            "--pagesize",
            huge_pagesize,
            "--directory",
            str(huge_dir),
        ]
    ).run()


def clear_hugepages(huge_dir: Union[str, Path] = Path("/mnt/huge")):
    """Unmount and clear previously allocated hugepages.

    Parameters
    ----------
    huge_dir : str or Path
        Path to the directory where hugepages are mounted.
    """

    executable.Tool(
        [
            "dpdk-hugepages",
            "--unmount",
            "--directory",
            str(huge_dir),
        ],
    ).run()
    executable.Tool(["dpdk-hugepages", "--clear"]).run()
