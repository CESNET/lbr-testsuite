"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Common functions for charts drawing.
"""

import math
import os
import pathlib

from pytest_cases import fixture

from lbr_testsuite import data_table


def mbps_to_mpps(thrpt_mbps, pkt_len):
    # Add 24B to packet lenth: 7B preamble + 1B SoF + 4B CRC + 12B minimal IFG
    pps = thrpt_mbps / ((pkt_len + 24) * 8)
    pps = math.ceil(pps)  # just here for testing, to have "whole" packets
    return pps


@fixture(scope="module")
def results_filenames(request, tmp_path_factory):
    """Create a dictionary with filenames for results (csv, png) and
    reference files (csv, png).
    """

    tmp_path = tmp_path_factory.mktemp("data_table")
    ref_path = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    ref_path = ref_path / "reference_results"
    test_name = request.node.name[:-3]  # remove ".py" from test name

    test_base = tmp_path / test_name
    ref_base = ref_path / test_name

    return dict(
        ref_csv=f"{ref_base}.csv",
        ref_png=f"{ref_base}.png",
        test_csv=f"{test_base}.csv",
        test_png=f"{test_base}.png",
    )
