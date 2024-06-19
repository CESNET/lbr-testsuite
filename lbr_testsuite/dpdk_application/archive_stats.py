"""
Author(s): Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Module for archiving appliacation statistics.
"""

import logging


global_logger = logging.getLogger(__name__)


def _save_dict_to_file(data, path):
    with open(path, "w") as f:
        for k, v in data.items():
            f.write(f"{k}: {v}\n")


def archive_port_stats(
    application,
    out_dir,
):
    """Archive port statistics across all ports of given
    application. This function is designed to work with Protector
    and L3fwd classes.

    Parameters
    ----------
    application : Union[ProtectorRuntime, L3fwd, L3fwdMulti]
        Protector or L3fwd instance.
    out_dir : Path
        Output directory.

    Returns
    -------
    Path
        Filepath to the stored port statistics.
    """

    try:
        stats = application.get_stats()
    except Exception as e:
        global_logger.warning(f"Could not obtain port statistics: {e}")
        return None

    stats_path = out_dir / "dev_stats"
    _save_dict_to_file(stats, stats_path)
    return stats_path


def archive_port_xstats(
    application,
    out_dir,
):
    """Archive extended port statistics across all ports of
    given application. This function is designed to work with
    Protector and L3fwd classes.

    Parameters
    ----------
    application : Union[ProtectorRuntime, L3fwd, L3fwdMulti]
        Protector or L3fwd instance.
    out_dir : Path
        Output directory.

    Returns
    -------
    Path
        Filepath to the stored extended port statistics.
    """

    try:
        xstats = application.get_xstats()
    except Exception as e:
        global_logger.warning(f"Could not obtain port extended statistics: {e}")
        return None

    xstats_path = out_dir / "dev_xstats"
    _save_dict_to_file(xstats, xstats_path)
    return xstats_path

