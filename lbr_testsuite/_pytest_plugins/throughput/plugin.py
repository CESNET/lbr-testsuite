"""
Author(s):
    Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Common code for high-throughput tests and benchmarks.
"""

import copy
import csv
from datetime import datetime
from pathlib import Path

from pytest_cases import fixture

from lbr_testsuite.data_table import throughput_table


"""Name of a column with expected throughput value"""
EXPECTED_THROUGHPUT_COLUMN = "Expected throughput"


@fixture(scope="module")
def expect_file_name(request):
    """Path to the expectations file.

    By default, a file with the same name as a testfile (with ".csv"
    suffix instead of ".py").

    Redefine this fixture if "non-default" expectations file should
    be used.

    Parameters
    ----------
    request : fixture
        Special pytest fixture, here used for accessing test file name.

    Returns
    -------
    Path
        Path to a file with expected values for current benchmark test.
    """

    curr_test_filename = Path(request.node.fspath).stem
    expected_values_dir = Path(request.node.fspath).parent.resolve()

    return expected_values_dir / f"{curr_test_filename}.csv"


@fixture(scope="module")
def benchmark_params(expect_file_name):
    """Benchmark test parameters (i.e. expectation file index columns).

    Parameters
    ----------
    expect_file_name : Path
        Path to a file with expected values for current benchmark test.

    Returns
    -------
    list(str)
        List of parameter names.
    """

    mandatory_columns = [
        throughput_table.ThroughputTable.PACKET_LENGTH_COLUMN,
        EXPECTED_THROUGHPUT_COLUMN,
    ]

    with open(expect_file_name, "r") as f:
        reader = csv.DictReader(f)
        params = [c for c in reader.fieldnames if c not in mandatory_columns]

    return params


def min_required_performance():
    """If measured throughput is less than expected but still above this
    minimum (or equal), the measured value is recorded as a new
    expectation. If the measured value is lower than this minimum, it is
    considered an error and expected value is not adjusted.
    """

    return 0.95  # 95%


@fixture(scope="module")
def throughput_expectation(request, expect_file_name, benchmark_params, tmp_path_factory):
    """Fixture providing throughput table with expected values."""

    thrpt_expected = throughput_table.ThroughputTable(
        value_columns=[EXPECTED_THROUGHPUT_COLUMN],
        index_columns=benchmark_params,
    )
    thrpt_expected.load_rows(expect_file_name)
    thrpt_measured = copy.deepcopy(thrpt_expected)

    yield thrpt_expected, thrpt_measured

    # store actual measured values to new csv with current date in its filename
    date_str = datetime.now().strftime("%d_%m_%Y")
    measured_file_name = f"{expect_file_name.stem}-{date_str}"
    measured_file_name = tmp_path_factory.getbasetemp() / measured_file_name

    thrpt_measured.to_csv(measured_file_name)
