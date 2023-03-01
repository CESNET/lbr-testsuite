"""
Author(s):
Pavel Krobot <Pavel.Krobot@cesnet.cz>
Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of executable module Service class.
"""

import pathlib
import subprocess

import pytest

from lbr_testsuite.executable import Service, executable


TESTING_OUTPUT = "I am testing myself!"
SYSTEMD_SERVICE_PATH = pathlib.Path("/usr/lib/systemd/system")
HELPER_SERVICE_NAME = "lbr-testsuite-testing-helper.service"
HELPER_SERVICE_PATH = SYSTEMD_SERVICE_PATH / HELPER_SERVICE_NAME

# Note: old version of systemd on our systems does not support
# "file" for StandardOutput/StandardError
SERVICE_TEMPLATE = """
[Unit]
Description=Systemd service unit file for lbr-testsuite testing.

[Service]
ExecStartPre={pre_start}
ExecStart={app} {args}
ExecStartPost={post_start}
Type=simple
StandardOutput=null
StandardError=inherit
"""

SUCCESS_ARGS = "-f 10"
FAIL_ARGS = f"{SUCCESS_ARGS} -r 1"
STARTUP_FAIL_ARGS = "-r 1"


def helper_service_factory(helper_app_args, helper_pre_start="true", helper_post_start="true"):
    """
    Generate a testing service fixture with given parameters.

    Paramerers
    ----------
    helper_app_args: str
        Arguments passed to the testing helper application
        withn starting the service.

    helper_pre_start: str
        Command passed to the 'ExecStartPre' hook when starting
        the service. It defaults to a string 'true' which is a UNIX
        command to 'do nothing, successfully'.
    helper_post_start: str
        Command passed to the 'ExecStartPost' hook after starting
        the service. It defaults to a string 'true' which is a UNIX
        command to 'do nothing, successfully'.
    """

    @pytest.fixture
    def helper_service(require_root, helper_app):
        HELPER_SERVICE_PATH.write_text(
            SERVICE_TEMPLATE.format(
                pre_start=helper_pre_start,
                post_start=helper_post_start,
                app=helper_app,
                args=helper_app_args,
            )
        )

        executable.Tool(["systemctl", "daemon-reload"]).run()

        yield HELPER_SERVICE_NAME

        HELPER_SERVICE_PATH.unlink()
        executable.Tool(["systemctl", "daemon-reload"]).run()

    return helper_service


helper_srv_ok = helper_service_factory(SUCCESS_ARGS)
helper_srv_ok_delay_start = helper_service_factory(SUCCESS_ARGS, "sleep 2")
helper_srv_ok_delay_start_stop = helper_service_factory(SUCCESS_ARGS, "sleep 2", "sleep 2")
helper_srv_fail = helper_service_factory(FAIL_ARGS)
helper_srv_fail_delay_start = helper_service_factory(FAIL_ARGS, "sleep 2")
helper_srv_fail_startup = helper_service_factory(STARTUP_FAIL_ARGS)


@pytest.mark.systemd
def test_service_start_stop_nonblocking_success(helper_srv_ok):
    """Test successful start of a helper service.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=False)
    assert srv.is_active()
    srv.stop(blocking=False)
    ret = srv.returncode()
    assert ret == 0


@pytest.mark.systemd
def test_service_start_stop_nonblocking_fail(helper_srv_fail):
    """Test correct return code on failed service.

    Parameters
    ----------
    helper_srv_fail : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_fail)
    srv.start(blocking=False)
    assert srv.is_active()
    srv.stop(blocking=False)
    ret = srv.returncode()
    assert ret == 1


@pytest.mark.systemd
def test_service_start_stop_blocking_success(helper_srv_ok_delay_start):
    """Test successful start of a helper service after a delay.

    Parameters
    ----------
    helper_srv_ok_delay_start : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok_delay_start)
    srv.start(blocking=True)
    assert srv.is_active()
    srv.stop(blocking=True)
    ret = srv.returncode()
    assert ret == 0


@pytest.mark.systemd
def test_service_start_stop_blocking_fail(helper_srv_fail_delay_start):
    """Test correct return code of a failed exit after a delay.

    Parameters
    ----------
    helper_srv_fail_delay_start : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_fail_delay_start)
    srv.start(blocking=True)
    assert srv.is_active()
    srv.stop(blocking=True)
    ret = srv.returncode()
    assert ret == 1


@pytest.mark.systemd
def test_service_start_fail(helper_srv_fail_startup):
    """Test that error on startup raises an exception.

    Parameters
    ----------
    helper_srv_fail_startup : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_fail_startup)
    with pytest.raises((subprocess.CalledProcessError, RuntimeError)):
        srv.start(blocking=True)

    assert srv.is_active() is False


@pytest.mark.systemd
def test_service_is_active_not_started(helper_srv_ok):
    """Test that 'is_active()' returns correct value for
    service that is not started.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    assert srv.is_active() is False


@pytest.mark.systemd
def test_service_is_active_running(helper_srv_ok):
    """Test that 'is_active()' returns correct value for
    service that is running.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=False)
    assert srv.is_active()
    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_is_active_failed(helper_srv_fail_startup):
    """Test that 'is_active()' returns correct value for
    service that failed when starting.

    Parameters
    ----------
    helper_srv_fail : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_fail_startup)
    srv.start(blocking=False)
    assert srv.is_active() is False


@pytest.mark.systemd
def test_service_is_active_stopped(helper_srv_ok):
    """Test that 'is_active()' returns correct value for
    service that is successfuly stopped.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=False)
    srv.stop(blocking=False)
    assert srv.is_active() is False


@pytest.mark.systemd
def test_service_is_active_transitions(helper_srv_ok_delay_start_stop):
    """Test that 'is_active()' returns correct values for
    service not running, then is started and lastly stopped.

    Parameters
    ----------
    helper_srv_ok_delay_start_stop : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok_delay_start_stop)
    assert srv.is_active() is False
    srv.start(blocking=True)
    assert srv.is_active()
    srv.stop(blocking=True)
    assert srv.is_active() is False
