"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2021 CESNET

Keyboard interrupt pytest plug-in. The plugin solves the problem
of "keyboard interrupts" (not running all the teardown finalizers,
leaving allocated namespaces, veth interface, etc., when CTRL+C is
pressed). After CTRL+C and SIGINT is captured, pytest is switched
into a special "exiting" mode (efectivelly handling the Keybord
Interrupt exception). Unfortunatelly, if any registered finalizer
fails and raises an expecion this causes an internal error and
leads to not running the rest of finalizers (even if pytest not
in "exiting" mode can handle them correctly). The plugin thus
wraps all the finalizers into try-except block. This is enabled
by patching the internal pytest addfinalizer method of
FixtureRequest class. Such a wrapper starts to catch and log all
finalizer exceptions only if pytest is in "exiting" mode after
pressing CTRL+C. In "normal" mode exceptions are raised as expected
to be handled traditionally by pytest itself.
"""

import logging

import _pytest
import pytest


global_logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Standard pytest hook to handle command line or `pytest.ini` file
    options. It defines `lbr_keyboard_interrupt` ini option. This option allows
    user to choose whether he wishes to activate this plugin.
    """

    parser.addini(
        "lbr_keyboard_interrupt",
        type="bool",
        default=False,
        help=(
            "Convenience flag which allows user to explicitly enable/disable activation "
            "of this plugin."
        ),
    )


@pytest.hookimpl(tryfirst=True)
def pytest_keyboard_interrupt(excinfo):
    """Standard pytest hook to handle keyboard interrupts. We only set
    global variable `keyboard_interrupt` to True which changes the
    behaviour of all finalizers and switches them into "allow failures"
    mode.

    Parameters
    ----------
    parser : ExceptionInfo
        The captured exception
    """

    global keyboard_interrupt
    keyboard_interrupt = True


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """We register the functionality of the plugin in the standard pytest
    hook called when a session is started. The hookimpl decorator ensures
    executing this hook as soon as possible to prevent any other plugin
    from potentially adding a finalizer before the addfinalizer method is
    patched.

    Parameters
    ----------
    session : pytest.Session
        Pytest session object
    """

    # user didn't choose to use this plugin
    if not session.config.getini("lbr_keyboard_interrupt"):
        return

    global keyboard_interrupt
    keyboard_interrupt = False

    addfinalizer_old = _pytest.fixtures.FixtureRequest.addfinalizer

    def addfinalizer_new(self, finalizer):
        def finalizer_wrapped():
            try:
                finalizer()
            except Exception as e:
                if not keyboard_interrupt:
                    raise e

                global_logger.error(e)

        addfinalizer_old(self, finalizer_wrapped)

    _pytest.fixtures.FixtureRequest.addfinalizer = addfinalizer_new
