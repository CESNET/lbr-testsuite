"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Module for profiling of an application using port-load steps
measurements. These measurements gradually increase and decrease test
traffic load using predefined steps.
"""

import logging

from lbr_testsuite.profiling.rx_tx import ProfiledPipelineWithStatsSubject


global_logger = logging.getLogger(__name__)


"""Default duration of single step when "steps-profiling" is used."""
DEFAULT_STEP_DURATION = 2

"""Default steps for "steps-profiling". Steps are expressed as
a percentage of total test traffic load. Default steps begin from 10%
to 100% and then go back to 10% with 10% step (i.e. 10%, 20%,
30% ... 100%, 90%, ... 10%).
"""
DEFAULT_STEPS = list(range(10, 101, 10)) + list(range(90, 9, -10))


def profile_tx_rx_steps(
    spirent,
    stream_block,
    profiler,
    app,
    mpps,
    step_duration=DEFAULT_STEP_DURATION,
    steps=DEFAULT_STEPS,
):
    """Profile an application when processing packets send from
    the spirent and returning them back using traffic load steps.
    Traffic-load steps are percentages of maximal port load (mpps
    argument).

    Parameters
    ----------
    spirent : Spirent
        Instance of initialized spirent class with STC connected.
    stream_block : StreamBlock
        Testing stream block represented by StreamBlock object.
    profiler : Profiler
        Profiler to be used during packet generation.
    app : PipelineRuntime
        Started application prepared for packet processing which will be
        profiled.
    mpps : int
        Maximal load of used line in mega packets per second. It is used
        for evaluation of Rx/Tx packet count.
    step_duration : int, optional
        Duration of a single measurement step in seconds.
    steps : list, optional
        List of steps as a percentages of max load.

    Returns
    -------
    tuple(int, int)
        Returns a pair of statistics: total TX packets (first) and
        total RX packets (second).
    """

    pps = int(mpps * 1_000_000)
    tolerance = pps * (0.05)  # 5% tolerance

    spirent._stc_handler.stc_clear_results()
    spirent._stc_handler.stc_set_port_scheduling_mode("port")
    # We need to set some initial load as spirent does not react
    # dynamically to changes of load otherwise. It seems that it has
    # to be approximately at least 1000 fps. We doubled the value
    # just to be sure...
    spirent.set_port_load("fps", 2000)
    spirent._stc_handler.stc_start_generators()

    global_logger.debug(f"Starting measurements with maximal port load is {pps:_} pps.")
    try:
        profiler.start(ProfiledPipelineWithStatsSubject(app))

        for s in steps:
            pps_step = int(pps * (s / 100))
            global_logger.debug(
                f"Measuring throughput at {s}% of maximal port load ({pps_step:_} pps)."
            )
            spirent.set_port_load("fps", pps_step)
            time.sleep(step_duration)

            measured_pps = stream_block._read_stats("FrameRate")[0]  # 0 for TX frame-rate
            global_logger.debug(f"Frame rate: {measured_pps:_}")
            rate_is_as_expected = pps_step - tolerance <= measured_pps <= pps_step + tolerance
            assert rate_is_as_expected, f"{s}% of {pps:_} Mpps: unexpected rate: {measured_pps:_}"

        profiler.stop()
    finally:
        spirent._stc_handler.stc_stop_generators()

    spirent._stc_handler.stc_refresh_results()
    stats = stream_block.get_tx_rx_stats()
    return stats["tx"]["FrameCount"], stats["rx"]["FrameCount"]
