"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Common pytest fixtures and hooks for testsuite tests.
"""

import logging

from pytest import fixture


def pytest_addoption(parser):
    parser.addoption(
        "--remote-host",
        type=str,
        default=None,
        help=(
            "Host where remote variants of tests should run. "
            "If not set, skip remote variants of tests."
        ),
    )

    parser.addoption(
        "--local-interface",
        type=str,
        action="store",
        help=(
            "Local interface where all traffic is received and sent from. "
            "Used for throughput runner tests."
        ),
    )


def pytest_configure(config):
    """pytest_configure hook is used here to restrict selected loggers
    to higher severity messages only.
    """

    restricted_loggers = [
        "faker.factory",
        "urllib3.connectionpool",
        "lbr_testsuite.spirent.spirent",
        "STC",
    ]
    for rl in restricted_loggers:
        logging.getLogger(rl).setLevel(logging.WARNING)


@fixture(scope="session")
def local_interface(request):
    """Local interface where all traffic is received and sent from.

    Returns
    -------
    str
        Interface name.
    """

    return request.config.getoption("local_interface")
