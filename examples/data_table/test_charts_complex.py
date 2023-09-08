"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of charts creation via data_table module - complex case with
parametrization over mocked routing mode and count of workers.
Two charts in single row (one for bits, one for packets) are created
for all measurements and separately for routing modes.
"""

import logging

import pytest
from pytest_cases import fixture, parametrize

from lbr_testsuite import data_table

from .conftest import mbps_to_mpps


global_logger = logging.getLogger(__name__)


"""Test measures throughput for selected packet lengths."""
PACKET_LENGTHS = [72, 128, 256, 512, 1024, 1500]


"""In a real test line speed would be somehow determined in used
environment.
"""
LINE_SPEED = 100 * 1000


"""Expected throughput for tested packet lengths and count of workers."""
EXPECTED_VALUES = {
    72: {1: 10 * 1000, 8: 20 * 1000, 16: 50 * 1000},
    128: {1: 40 * 1000, 8: 60 * 1000, 16: 80 * 1000},
    256: {1: 40 * 1000, 8: 60 * 1000, 16: 80 * 1000},
    512: {1: 40 * 1000, 8: 60 * 1000, 16: 80 * 1000},
    1024: {1: 50 * 1000, 8: 80 * 1000, 16: LINE_SPEED},
    1500: {1: 50 * 1000, 8: 80 * 1000, 16: LINE_SPEED},
}


"""Values for testing. In a real tests these are results of real
measuring.
"""
TESTING_MEASUREMENTS_TABLE = {
    "routing_AB": {
        1: {
            72: 5 * 1000,
            128: 20 * 1000,
            256: 30 * 1000,
            512: 40 * 1000,
            1024: 40 * 1000,
            1500: 40 * 1000,
        },
        8: {
            72: 20 * 1000,
            128: 50 * 1000,
            256: 10 * 1000,
            512: 50 * 1000,
            1024: 70 * 1000,
            1500: 70 * 1000,
        },
        16: {
            72: 40 * 1000,
            128: 70 * 1000,
            256: 70 * 1000,
            512: 70 * 1000,
            1024: LINE_SPEED,
            1500: LINE_SPEED,
        },
    },
    "routing_XY": {
        1: {
            72: 5 * 1000,
            128: 25 * 1000,
            256: 35 * 1000,
            512: 45 * 1000,
            1024: 45 * 1000,
            1500: 45 * 1000,
        },
        8: {
            72: 25 * 1000,
            128: 55 * 1000,
            256: 15 * 1000,
            512: 55 * 1000,
            1024: 75 * 1000,
            1500: 75 * 1000,
        },
        16: {
            72: 45 * 1000,
            128: 75 * 1000,
            256: 75 * 1000,
            512: 75 * 1000,
            1024: LINE_SPEED,
            1500: LINE_SPEED,
        },
    },
}


@fixture
@parametrize(pl=PACKET_LENGTHS)
def packet_length(pl):
    return pl


@fixture(scope="module")
@parametrize(workers=[1, 8, 16])
def workers_count(request, workers):
    return workers


ROUTING_MODES = ["routing_AB", "routing_XY"]


@fixture(scope="module")
@parametrize("routing_mode", ROUTING_MODES)
def routing_mode(request, routing_mode):
    return routing_mode


@fixture
def some_tested_device(routing_mode, workers_count):
    # configure the device, here only pick related testing measurements
    return TESTING_MEASUREMENTS_TABLE[routing_mode][workers_count]


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
    p_bits = bc.chart_spec("Mbps", "Bits Throughput", parametrized_by=["workers", "routing"])
    p_pkts = bc.chart_spec("Mpps", "Packets Throughput", parametrized_by=["workers", "routing"])
    ch.append_charts_row([p_bits, p_pkts])

    for r in ROUTING_MODES:
        if r not in measurements.get_column_unique_values("routing"):
            # routing mode was not measured (e.g. unselected via "-k" parameter)
            continue

        # Per-routing-mode measurements
        p_bits = bc.chart_spec(
            "Mbps",
            f"bits - {r}",
            parametrized_by="workers",
            filter_by=dict(routing=r),
        )
        p_pkts = bc.chart_spec(
            "Mpps",
            f"packets - {r}",
            parametrized_by="workers",
            filter_by=dict(routing=r),
        )
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

    dt = data_table.DataTable(
        data_table.BenchmarkCharts().BASE_COLUMNS_HEADER + ["workers", "routing"]
    )

    yield dt

    if not dt.empty():
        global_logger.debug(f"Storing measurements to: {results_filenames['test_csv']}")
        dt.store_csv(csv_file=results_filenames["test_csv"])

        store_charts(dt, results_filenames["test_png"])


def measure_throughput(device, packet_length):
    # measuring ...
    m = device[packet_length]
    return m, mbps_to_mpps(m, packet_length)


def test_charts_complex(
    measurements,
    some_tested_device,
    packet_length,
    workers_count,
    routing_mode,
):
    """For every packet length measure throughput and store measurement
    in a data table "measurements". Measured data are stored and plotted
    within the cleanup phase.
    """

    max_throughput = determine_line_speed()

    expected_bytes = EXPECTED_VALUES[packet_length][workers_count]

    measured_bytes, measured_packets = measure_throughput(some_tested_device, packet_length)

    measurements.append_row(
        (
            packet_length,
            measured_bytes,
            expected_bytes,
            max_throughput,
            measured_packets,
            mbps_to_mpps(expected_bytes, packet_length),
            mbps_to_mpps(max_throughput, packet_length),
            workers_count,
            routing_mode,
        ),
    )

    """Uncomment following assert to see tests evaluation. This will
    produce some tests failures as some testing measurements are set
    to lower values than expected.
    """
    # assert  measured_bytes >= expected_bytes
