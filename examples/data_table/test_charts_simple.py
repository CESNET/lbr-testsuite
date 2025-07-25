"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of charts creation via data_table module - simple case with
two charts in single row (one for bits, one for packets). No
parametrization or filtering is used.
"""

import logging

import pytest
from pytest_cases import fixture, parametrize

from lbr_testsuite import data_table
from lbr_testsuite.common.conv import mbps_to_mpps


global_logger = logging.getLogger(__name__)


"""Test measures throughput for selected packet lengths."""
PACKET_LENGTHS = [72, 128, 256, 512, 1024, 1500]


"""In a real test line speed would be somehow determined in used
environment.
"""
LINE_SPEED = 100 * 1000


"""Expected throughput for tested packet lengths."""
EXPECTED_VALUES = {
    72: 50 * 1000,
    128: 80 * 1000,
    256: 80 * 1000,
    512: 80 * 1000,
    1024: LINE_SPEED,
    1500: LINE_SPEED,
}


"""Values for testing. In a real tests these are results of real
measuring.
"""
TESTING_MEASUREMENTS_TABLE = {
    72: 10 * 1000,
    128: 80 * 1000,
    256: 40 * 1000,
    512: 80 * 1000,
    1024: 90 * 1000,
    1500: 90 * 1000,
}


@fixture
@parametrize(pl=PACKET_LENGTHS)
def packet_length(pl):
    return pl


def determine_line_speed():
    """In real world, do something clever..."""

    return LINE_SPEED


def store_charts(measurements, png_file):
    """Store charts from measurements as PNG file.

    Two charts in single row - measurement in bits (first) and
    packets (second).
    """

    ch = data_table.charts.DataTableCharts()
    bc = data_table.BenchmarkCharts()

    # Summary of all measurements
    p_bits = bc.chart_spec("Mbps", "Bits Throughput")
    p_pkts = bc.chart_spec("Mpps", "Packets Throughput")
    ch.append_charts_row([p_bits, p_pkts])

    ch.set_data(measurements)

    global_logger.debug(f"Storing charts to: {png_file}")
    ch.store_charts(png_file, title="Testing Measurement of Throughput")


@fixture(scope="module")
def measurements(results_filenames):
    """Preparation of data container for throughput measurements.

    Parameters
    ----------
    results_filenames : dict(str, pathlib.Path)
        Provide filenames for results from this test and reference
        results files

    Returns
    -------
    DataTable
        Created instance of our custom data container (based
        on pandas.DataTable).
    """

    dt = data_table.DataTable(data_table.BenchmarkCharts().BASE_COLUMNS_HEADER)

    yield dt

    if not dt.empty():
        global_logger.debug(f"Storing measurements to: {results_filenames['test_csv']}")
        dt.store_csv(csv_file=results_filenames["test_csv"])

        store_charts(dt, results_filenames["test_png"])


def measure_throughput(packet_length):
    # measuring ...
    m = TESTING_MEASUREMENTS_TABLE[packet_length]
    return m, mbps_to_mpps(m, packet_length)


def test_charts_simple(
    measurements,
    packet_length,
):
    """For every packet length measure throughput and store measurement
    in a data table "measurements". Measured data are stored and plotted
    within the cleanup phase.
    """

    max_throughput = determine_line_speed()

    expected_bytes = EXPECTED_VALUES[packet_length]
    measured_bytes, measured_packets = measure_throughput(packet_length)

    measurements.append_row(
        (
            packet_length,
            measured_bytes,
            expected_bytes,
            max_throughput,
            measured_packets,
            mbps_to_mpps(expected_bytes, packet_length),
            mbps_to_mpps(max_throughput, packet_length),
        ),
    )

    """Uncomment following assert to see tests evaluation. This will
    produce some tests failures as some testing measurements are set
    to lower values than expected.
    """
    # assert  measured_bytes >= expected_bytes
