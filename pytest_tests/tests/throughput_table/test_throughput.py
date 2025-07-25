"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2024 CESNET, z.s.p.o.
"""

import logging
import os
from enum import StrEnum
from pathlib import Path

import pytest
from pytest_cases import fixture, parametrize

from lbr_testsuite.common.conv import mbps_to_mpps, mpps_to_mbps
from lbr_testsuite.data_table import throughput_table
from lbr_testsuite.data_table.benchmark_charts import BenchmarkCharts
from lbr_testsuite.data_table.charts import DataTableCharts
from lbr_testsuite.data_table.data_table import DataTable


global_logger = logging.getLogger(__name__)

RoutingMode = ["acl", "simple", "mlx5"]


EXP_THROUGHPUT_COLUMN = "Expected throughput"
THROUGHPUT_EXPECTATION = throughput_table.ThroughputTable(
    value_columns=[EXP_THROUGHPUT_COLUMN],
    index_columns=["driver", "workers"],
)
THROUGHPUT_EXPECTATION.load_rows(Path(__file__).parent.resolve() / "expected_throughput.csv")


MEASUREMENTS_FILENAME = "throughput_measurements"


@fixture
@parametrize(packet_lengths=[64, 128, 256, 512, 1024, 1500])
def packet_length(packet_lengths):
    return packet_lengths


@fixture(scope="module")
@parametrize(workers=[8, 16])
def protector_workers_count(request, workers):
    return workers


@fixture(scope="module")
def _nic_driver(request):
    return request.config.getoption("nic_driver")


def compose_output_path(pyt_request, target, suffix=""):
    tmp_dir_global = cwd = os.getcwd()

    valid_file_name = pyt_request.node.name.replace("/", "-")
    suffix = f"__{valid_file_name}{suffix}"

    target_path = f"{str(target)}{suffix}"
    return Path(tmp_dir_global) / target_path


def _store_charts(pyt_request, measurements, file):
    ch = DataTableCharts()
    bc = BenchmarkCharts()

    # Summary of all measurements
    p_bits = bc.chart_spec("Mbps", "Mbps", parametrized_by=["workers"])
    p_pkts = bc.chart_spec("Mpps", "Mpps", parametrized_by=["workers"])
    ch.append_charts_row([p_bits, p_pkts])

    ch.set_data(measurements)
    png_file_name = compose_output_path(pyt_request, file, ".png")

    ch.store_charts(png_file_name, title="DCPro Protector Throughput")


@fixture(scope="module")
def measurements(request):
    """Preparation of data container for throughput measurements.

    Parameters
    ----------
    request : FixtureRequest
        Special pytest fixture.

    Returns
    -------
    DataTable
        Created instance of our custom DataTable class (based
        on pandas.DataTable).
    """

    params = ["workers"]
    thrpt_tbl = throughput_table.ThroughputTable(throughput_table.COMMON_VALUES_COLUMNS, params)

    yield thrpt_tbl

    if not thrpt_tbl.empty():
        csv_file_name = compose_output_path(request, MEASUREMENTS_FILENAME, ".csv")
        thrpt_tbl.to_csv(csv_file_name)

        _store_charts(request, thrpt_tbl.df, MEASUREMENTS_FILENAME)

        print()
        print(csv_file_name)


def test_throughput(
    request,
    protector_workers_count,
    packet_length,
    measurements,
    _nic_driver,
):
    """Simple "fake" throughput measurements test

    Test simulates measurements of throughput with different parameters
    (NIC driver and worker count). Measured values are stored
    as CSV and plotted into a chart.
    """

    exp_throughput = THROUGHPUT_EXPECTATION.get(
        {
            "driver": _nic_driver,
            "workers": protector_workers_count,
            measurements.PACKET_LENGTH_COLUMN: packet_length,
        }
    )

    max_throughput = 100_000

    mbps = int(exp_throughput * 0.9)
    mpps = mbps_to_mpps(mbps, packet_length)

    measurements.append_row(
        {
            measurements.PACKET_LENGTH_COLUMN: packet_length,
            "workers": protector_workers_count,
            throughput_table.VALUE_COLUMN.MBPS: mbps,
            throughput_table.VALUE_COLUMN.EXP_MBPS: exp_throughput,
            throughput_table.VALUE_COLUMN.MAX_MBPS: max_throughput,
            throughput_table.VALUE_COLUMN.MPPS: mpps,
            throughput_table.VALUE_COLUMN.EXP_MPPS: mbps_to_mpps(exp_throughput, packet_length),
            throughput_table.VALUE_COLUMN.MAX_MPPS: mbps_to_mpps(max_throughput, packet_length),
        }
    )
