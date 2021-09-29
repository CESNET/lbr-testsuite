"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Common pytest fixtures and hooks for testsuite tests.
"""

import logging


def pytest_configure(config):
    """pytest_configure hook is used here to restrict selected loggers
    to higher severity messages only.
    """

    restricted_loggers = [
        'faker.factory',
        'urllib3.connectionpool',
        'lbr_testsuite.spirent.spirent',
        'STC',
    ]
    for rl in restricted_loggers:
        logging.getLogger(rl).setLevel(logging.WARNING)
