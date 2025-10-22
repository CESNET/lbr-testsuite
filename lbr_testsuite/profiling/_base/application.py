"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021-2025 CESNET, z.s.p.o.

A component for application construction and usage of profilers.

Functions defined here are primarily intended for common usage of
profilers either with pytest or a standalone application.
"""

import argparse
import functools
from pathlib import Path
from typing import Callable

from pypapi import events

from .._profilers.cache import PAPIProfiler
from .._profilers.cpumon import CPUMonProfiler
from .._profilers.perf import Perf, PerfC2C, PerfMem, PerfStat
from .._profilers.pipeline import PipelineMonProfiler
from .._profilers.power_consumption import pyJoulesProfiler
from .._profilers.rx_tx import RxTxMonProfiler
from .._profilers.system import IrqMonProfiler
from .concurrent_engine import ConcurrentEngine
from .profiler import Profiler
from .thread_engine import ThreadEngine


def add_cli_arguments(add_argument_cbk: Callable):
    """Add CLI arguments for enabling and configuration of profilers.

    Parameters
    ----------
    add_argument_cbk: Callable
        A callable which accepts arguments as same as
        argparse.ArgumentParser.add_argument function.

    Example of usage with argparse.ArgumentParser:
    ```
    import argparse

    from lbr_testsuite.profiling import application


    parser = argparse.ArgumentParser(prog="Example", description="not today...")

    application.add_cli_arguments(parser.add_argument)

    args = parser.parse_args()

    if args.use_cpumon:
        print("Uh-oh, it works!")

    # test with ./<app_name> --use-cpumon
    # or with help: ./<app_name> --help
    ```
    """

    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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
    add_argument_cbk(
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


def collect_profilers(
    get_option_cbk: Callable[[int], any] | None = None,
    path_compose_cbk: Callable[[str, str | None, str | None], str] | None = None,
    profilers_output_dir: str = "./",
    parsed_args: argparse.Namespace | None = None,
    concurrent_engine: type[ConcurrentEngine] = ThreadEngine,
) -> list[Profiler]:
    """Collect profilers based on parsed CLI arguments.

    Parameters
    ----------
    get_option_cbk: Callable | None = None
        Function for acquiring of single option. This functions should
        take single argument (an option name) and should return
        the option value. If this callback is not set, default argparse
        way is used (`parsed_args` value has to be set in this case).
    path_compose_cbk: Callable | None = None
        Function for profilers output path composition. Function should
        take one mandatory argument (profiler identification string) and
        two optional arguments - file suffix and output director path.
        Function should return composed path.
    profilers_output_dir: str = "./"
        Path to a directory for profilers output files.
    parsed_args: argparse.Namespace | None = None
        Parsed arguments.use this parameter only when `get_option_cbk`
        is not used.
    concurrent_engine: type[ConcurrentEngine], optional
        Engine used for concurrent execution of profilers.

    Returns
    -------
    list[Profiler]
        List of initialized profilers instances.

    Example of usage with argparse:
    ```
    ...extending example from add_cli_arguments() function

    args = parser.parse_args()

    profilers = application.collect_profilers()

    ...

    ```
    """

    if not get_option_cbk:
        assert parsed_args, "Cannot use default argument parser without parsed arguments."
        get_option_cbk = functools.partial(getattr, parsed_args)

    if not path_compose_cbk:

        def default_path_compose(target, suffix="", directory=""):
            return str(Path(directory) / f"{target}{suffix}")

        path_compose_cbk = default_path_compose

    profilers = []

    use_perf = get_option_cbk("use_perf")
    if use_perf is not None:
        args = use_perf.split(" ")
        data = path_compose_cbk("perf_std", ".data", profilers_output_dir)
        profilers.append(Perf(data, args=args))

    use_perf_stat = get_option_cbk("use_perf_stat")
    if use_perf_stat is not None:
        args = use_perf_stat.split(" ")
        data = path_compose_cbk("perf_stat", ".data", profilers_output_dir)
        profilers.append(PerfStat(data, args=args))

    use_perf_mem = get_option_cbk("use_perf_mem")
    if use_perf_mem is not None:
        args = use_perf_mem.split(" ")
        data = path_compose_cbk("perf_mem", ".data", profilers_output_dir)
        profilers.append(PerfMem(data, args=args))

    use_perf_c2c = get_option_cbk("use_perf_c2c")
    if use_perf_c2c is not None:
        args = use_perf_c2c.split(" ")
        data = path_compose_cbk("perf_c2c", ".data", profilers_output_dir)
        profilers.append(PerfC2C(data, args=args))

    use_pyJoules = get_option_cbk("use_pyJoules")
    if use_pyJoules:
        if use_pyJoules == "auto":
            numa_sockets = None  # auto-detection
        else:
            numa_sockets = [int(s) for s in use_pyJoules.split(",")]

        out_file_base = path_compose_cbk("pyJoules", directory=profilers_output_dir)
        profilers.append(
            pyJoulesProfiler(
                numa_sockets=numa_sockets,
                output_file_base=out_file_base,
                concurrent_engine_cls=concurrent_engine,
            )
        )

    use_cpumon = get_option_cbk("use_cpumon")
    if use_cpumon:
        if use_cpumon <= 0:
            raise Exception(f"invalid scaling-period for cpumon: {use_cpumon}")

        out_file_base_pattern = path_compose_cbk("cpumon{0}", directory=profilers_output_dir)
        time_step = use_cpumon
        profilers.append(
            CPUMonProfiler(
                time_step=time_step,
                output_file_base=out_file_base_pattern,
                concurrent_engine_cls=concurrent_engine,
            )
        )

    use_pipelinemon = get_option_cbk("use_pipelinemon")
    if use_pipelinemon:
        if use_pipelinemon <= 0:
            raise Exception(f"invalid scaling-period for pipelinemon: {use_pipelinemon}")

        out_file_base_pattern = path_compose_cbk("pipelinemon{0}", directory=profilers_output_dir)
        time_step = use_pipelinemon
        profilers.append(
            PipelineMonProfiler(
                time_step=time_step,
                output_file_base=out_file_base_pattern,
                concurrent_engine_cls=concurrent_engine,
            )
        )

    use_rxtxmon = get_option_cbk("use_rxtxmon")
    if use_rxtxmon:
        if use_rxtxmon <= 0:
            raise Exception(f"invalid scaling-period for rxtxmon: {use_rxtxmon}")

        out_file_base = path_compose_cbk("rxtxmon", directory=profilers_output_dir)
        profilers.append(
            RxTxMonProfiler(
                time_step=use_rxtxmon,
                output_file_base=out_file_base,
                concurrent_engine_cls=concurrent_engine,
            )
        )

    use_irqmon = get_option_cbk("use_irqmon")
    if use_irqmon:
        if use_irqmon <= 0:
            raise Exception(f"invalid scaling-period for irqmon: {use_irqmon}")

        out_file_base = path_compose_cbk("irqmon", directory=profilers_output_dir)
        time_step = use_irqmon
        profilers.append(
            IrqMonProfiler(
                time_step=time_step,
                output_file_base=out_file_base,
                concurrent_engine_cls=concurrent_engine,
            )
        )

    use_cache_prof = get_option_cbk("use_cache_prof")
    if use_cache_prof:
        if use_cache_prof <= 0:
            raise Exception(f"invalid scaling-period for irqmon: {use_cache_prof}")

        out_file_base = path_compose_cbk("cache_prof", directory=profilers_output_dir)
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
            PAPIProfiler(
                papi_evs,
                time_step=time_step,
                output_file_base=out_file_base,
                concurrent_engine_cls=concurrent_engine,
            ),
        )

    return profilers
