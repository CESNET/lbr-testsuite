"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Pytest plugin with profiler fixtures.
"""

from pypapi import events
from pytest_cases import fixture

from ...common.common import compose_output_path
from ...profiling.cache import PAPIProfiler
from ...profiling.cpumon import CPUMonProfiler
from ...profiling.perf import Perf, PerfC2C, PerfMem, PerfStat
from ...profiling.pipeline import PipelineMonProfiler
from ...profiling.power_consumption import pyJoulesProfiler
from ...profiling.profiler import MultiProfiler
from ...profiling.rx_tx import RxTxMonProfiler
from ...profiling.system import IrqMonProfiler


def pytest_addoption(parser):
    parser.addoption(
        "--use-perf",
        metavar="options",
        nargs="?",
        type=str,
        default=None,
        const="",
        help=(
            "Enable profiler perf. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-perf-stat",
        metavar="options",
        nargs="?",
        type=str,
        default=None,
        const="",
        help=(
            "Enable profiler perf stat. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-perf-mem",
        metavar="options",
        nargs="?",
        type=str,
        default=None,
        const="",
        help=(
            "Enable profiler perf mem. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-perf-c2c",
        metavar="options",
        nargs="?",
        type=str,
        default=None,
        const="",
        help=(
            "Enable profiler perf c2c. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-pyJoules",
        metavar="numa-sockets",
        nargs="?",
        type=str,
        default=None,
        const="auto",
        help=(
            "Enable profiler pyJoules. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-cpumon",
        metavar="sampling-period",
        nargs="?",
        type=float,
        default=None,
        const=0.1,
        help=(
            "Enable profiler cpumon. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-pipelinemon",
        metavar="sampling-period",
        nargs="?",
        type=float,
        default=None,
        const=0.05,
        help=(
            "Enable profiler pipelinemon. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )
    parser.addoption(
        "--use-irqmon",
        metavar="sampling-period",
        nargs="?",
        type=float,
        default=None,
        const=0.05,
        help=(
            "Enable interrupt monitoring profiler. It samples interrupts counts delivered "
            "to particular CPUs."
        ),
    )
    parser.addoption(
        "--use-rxtxmon",
        metavar="sampling-period",
        nargs="?",
        type=float,
        default=None,
        const=0.05,
        help=(
            "Enable Rx/Tx monitoring profiler. It samples Rx/Tx statistics (global and per-worker)."
        ),
    )
    parser.addoption(
        "--use-cache-prof",
        metavar="sampling-period",
        nargs="?",
        type=float,
        default=None,
        const=0.05,
        help=(
            "Enable cache profiler. Tests that are capable of using profilers "
            "would use it automatically."
        ),
    )


def collect_profilers(pyt_request, output_dir):
    profilers = []

    use_perf = pyt_request.config.getoption("use_perf")
    if use_perf is not None:
        args = use_perf.split(" ")
        data = compose_output_path(pyt_request, "perf_std", ".data", output_dir)
        profilers.append(Perf(data, args=args))

    use_perf_stat = pyt_request.config.getoption("use_perf_stat")
    if use_perf_stat is not None:
        args = use_perf_stat.split(" ")
        data = compose_output_path(pyt_request, "perf_stat", ".data", output_dir)
        profilers.append(PerfStat(data, args=args))

    use_perf_mem = pyt_request.config.getoption("use_perf_mem")
    if use_perf_mem is not None:
        args = use_perf_mem.split(" ")
        data = compose_output_path(pyt_request, "perf_mem", ".data", output_dir)
        profilers.append(PerfMem(data, args=args))

    use_perf_c2c = pyt_request.config.getoption("use_perf_c2c")
    if use_perf_c2c is not None:
        args = use_perf_c2c.split(" ")
        data = compose_output_path(pyt_request, "perf_c2c", ".data", output_dir)
        profilers.append(PerfC2C(data, args=args))

    use_pyJoules = pyt_request.config.getoption("use_pyJoules")
    if use_pyJoules:
        if use_pyJoules == "auto":
            numa_sockets = None  # auto-detection
        else:
            numa_sockets = [int(s) for s in use_pyJoules.split(",")]

        csv_file = compose_output_path(pyt_request, "pyJoules", ".csv", output_dir)
        charts_file = compose_output_path(pyt_request, "pyJoules", ".html", output_dir)
        profilers.append(pyJoulesProfiler(csv_file, charts_file, numa_sockets=numa_sockets))

    use_cpumon = pyt_request.config.getoption("use_cpumon")
    if use_cpumon:
        if use_cpumon <= 0:
            raise Exception(f"invalid scaling-period for cpumon: {use_cpumon}")

        csv_file_pattern = compose_output_path(pyt_request, "cpumon_{0}", ".csv", output_dir)
        charts_file_pattern = compose_output_path(pyt_request, "cpumon_{0}", ".html", output_dir)
        time_step = use_cpumon
        profilers.append(CPUMonProfiler(csv_file_pattern, charts_file_pattern, time_step=time_step))

    use_pipelinemon = pyt_request.config.getoption("use_pipelinemon")
    if use_pipelinemon:
        if use_pipelinemon <= 0:
            raise Exception(f"invalid scaling-period for pipelinemon: {use_pipelinemon}")

        csv_file_pattern = compose_output_path(pyt_request, "pipelinemon_{0}", ".csv", output_dir)
        mark_file = compose_output_path(pyt_request, "pipelinemon", ".mark", output_dir)
        charts_file_pattern = compose_output_path(
            pyt_request,
            "pipelinemon_{0}_{1}",
            ".html",
            output_dir,
        )
        time_step = use_pipelinemon
        profilers.append(
            PipelineMonProfiler(
                csv_file_pattern, mark_file, charts_file_pattern, time_step=time_step
            )
        )

    use_rxtxmon = pyt_request.config.getoption("use_rxtxmon")
    if use_rxtxmon:
        if use_rxtxmon <= 0:
            raise Exception(f"invalid scaling-period for rxtxmon: {use_rxtxmon}")

        csv_file = compose_output_path(pyt_request, "rxtxmon", ".csv", output_dir)
        mark_file = compose_output_path(pyt_request, "rxtxmon", ".mark", output_dir)
        charts_file = compose_output_path(pyt_request, "rxtxmon", ".html", output_dir)
        profilers.append(RxTxMonProfiler(csv_file, mark_file, charts_file, time_step=use_rxtxmon))

    use_irqmon = pyt_request.config.getoption("use_irqmon")
    if use_irqmon:
        if use_irqmon <= 0:
            raise Exception(f"invalid scaling-period for irqmon: {use_irqmon}")

        csv_file = compose_output_path(pyt_request, "irqmon", ".csv", output_dir)
        charts_file = compose_output_path(pyt_request, "irqmon", ".html", output_dir)
        time_step = use_irqmon
        profilers.append(IrqMonProfiler(csv_file, charts_file, time_step=time_step))

    use_cache_prof = pyt_request.config.getoption("use_cache_prof")
    if use_cache_prof:
        if use_cache_prof <= 0:
            raise Exception(f"invalid scaling-period for irqmon: {use_cache_prof}")

        csv_file = compose_output_path(pyt_request, "cache_prof", ".csv", output_dir)
        mark_file = compose_output_path(pyt_request, "cache_prof", ".mark", output_dir)
        charts_file = compose_output_path(pyt_request, "cache_prof", ".html", output_dir)
        time_step = use_cache_prof
        papi_evs = {
            "L1 Misses": [
                events.PAPI_L1_DCM,
                events.PAPI_L1_ICM,
            ],
            "L2 Hits": [
                events.PAPI_L2_DCH,
                events.PAPI_L2_ICH,
            ],
            "L2 Misses": [
                events.PAPI_L2_DCM,
                events.PAPI_L2_ICM,
            ],
            "L3 Accesses": [
                events.PAPI_L3_DCA,
                events.PAPI_L3_ICA,
            ],
        }
        profilers.append(
            PAPIProfiler(csv_file, mark_file, charts_file, papi_evs, time_step=time_step),
        )

    return profilers


@fixture(scope="function")
def profilers_output_dir():
    """Define a directory where all profilers output will be placed.

    Redefine this fixture to change the directory. By default, outputs
    are stored in the current working directory.

    Returns
    -------
    str
        Path to a directory for profilers output.
    """

    return ""


@fixture(scope="function")
def profiler(request, profilers_output_dir):
    prof = MultiProfiler(collect_profilers(request, profilers_output_dir))

    yield prof

    prof.stop()
