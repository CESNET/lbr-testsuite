"""
Author(s):
Pavel Krobot <Pavel.Krobot@cesnet.cz>
Kamil Vojanec <vojanec@cesnet.cz>
Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Testing of executable module Service class.
"""

import functools
import pathlib
import time
from datetime import datetime

import pytest

import lbr_testsuite
from lbr_testsuite.executable import Service, executable


TESTING_OUTPUT = "I am testing myself!"
SYSTEMD_SERVICE_PATH = pathlib.Path("/usr/lib/systemd/system")
HELPER_SERVICE_NAME = "lbr-testsuite-testing-helper.service"
HELPER_SERVICE_PATH = SYSTEMD_SERVICE_PATH / HELPER_SERVICE_NAME

SERVICE_DESCRIPTION = "Systemd service unit file for lbr-testsuite testing."
SERVICE_TYPE = "simple"

# Note: old version of systemd on our systems does not support
# "file" for StandardOutput/StandardError
SERVICE_TEMPLATE = """
[Unit]
Description={description}

[Service]
ExecStartPre={pre_start}
ExecStart={app} {args}
ExecStartPost={post_start}
ExecReload=touch {reload_file}
Type={service_type}
StandardOutput=null
StandardError=inherit
"""

SUCCESS_ARGS = "-f 10"
FAIL_ARGS = f"{SUCCESS_ARGS} -r 1"
STARTUP_FAIL_ARGS = "-r 1"
EXIT_DELAY_ARGS = "-d 2"

TIME_MEASUREMENT_TOLERANCE = 0.2


def _reload_file(tmp):
    return tmp / "reloaded"


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
    def helper_service(require_root, helper_app_local, tmp_path):
        HELPER_SERVICE_PATH.write_text(
            SERVICE_TEMPLATE.format(
                description=SERVICE_DESCRIPTION,
                service_type=SERVICE_TYPE,
                pre_start=helper_pre_start,
                post_start=helper_post_start,
                app=helper_app_local,
                args=helper_app_args,
                reload_file=_reload_file(tmp_path),
            )
        )

        executable.Tool(["systemctl", "daemon-reload"]).run()

        yield HELPER_SERVICE_NAME

        HELPER_SERVICE_PATH.unlink()
        executable.Tool(["systemctl", "daemon-reload"]).run()

    return helper_service


helper_srv_ok = helper_service_factory(SUCCESS_ARGS)
helper_srv_delay_exit = helper_service_factory(EXIT_DELAY_ARGS)
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
    with pytest.raises((executable.ExecutableProcessError, RuntimeError)):
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

    Note: when service failing to start, ExecutableException
    is raised

    Parameters
    ----------
    helper_srv_fail : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_fail_startup)
    try:
        srv.start(blocking=False)
    except executable.ExecutableException:
        pass
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


@pytest.mark.systemd
def test_service_is_active_after3s_running(helper_srv_ok):
    """Test that 'is_active(after=3)' waits for 3 seconds and returns correct value for
    service that is running.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=True)
    t_start = time.time()
    assert srv.is_active(after=3)
    t_diff = time.time() - t_start
    assert t_diff > 3 and t_diff < 3 + TIME_MEASUREMENT_TOLERANCE
    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_is_active_after_2s_delay_exit(helper_srv_delay_exit):
    """Test that 'is_active(after=1)' waits for one second and checks
    the status of a running service. After that, another check is made
    after the service exits 'isactive(after=3)'.

    Parameters
    ----------
    helper_srv_delay_exit : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_delay_exit)
    srv.start(blocking=True)
    assert srv.is_active(after=1)
    t_start = time.time()
    assert not srv.is_active(after=3)
    t_diff = time.time() - t_start
    assert t_diff > 3 and t_diff < 3 + TIME_MEASUREMENT_TOLERANCE
    srv.stop(blocking=False)


def _get_start_time():
    stdout, _ = executable.Tool(
        [
            "systemctl",
            "show",
            HELPER_SERVICE_NAME,
            "--property",
            "ActiveEnterTimestamp",
        ]
    ).run()

    t = stdout.strip().split()[2]
    return datetime.strptime(t, "%H:%M:%S")


def _service_is_restarted(before, max_diff=20):
    """max_diff just to check that there is not some ridiculous values"""

    after = _get_start_time()
    return before < after and (after - before).total_seconds() < max_diff


@pytest.mark.systemd
def test_service_restart_nonblocking_success(helper_srv_ok):
    """Test successful restart of a helper service.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=True)
    assert srv.is_active()

    time.sleep(1)  # to ensure at least 1s start time diff

    before = _get_start_time()
    srv.restart(blocking=False)

    assert lbr_testsuite.wait_until_condition(functools.partial(_service_is_restarted, before), 5)
    assert srv.is_active()

    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_restart_blocking_success(helper_srv_ok):
    """Test successful restart of a helper service with waiting for
    completion.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=True)
    assert srv.is_active()

    time.sleep(1)  # to ensure at least 1s start time diff

    before = _get_start_time()
    srv.restart(blocking=True)

    assert _service_is_restarted(before)
    assert srv.is_active()

    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_start_by_restart(helper_srv_ok):
    """Test successful restart of a service that has not been
    started. This should just start the service.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    assert not srv.is_active()

    srv.restart(blocking=True)
    assert srv.is_active()

    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_reload_success(helper_srv_ok, tmp_path):
    """Test successful reload of a helper service.

    Parameters
    ----------
    helper_srv_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=True)
    assert srv.is_active()

    assert not _reload_file(tmp_path).is_file()

    srv.reload()

    assert _reload_file(tmp_path).is_file()
    assert srv.is_active()

    srv.stop(blocking=False)


@pytest.mark.systemd
def test_service_parse_systemd_properties(helper_srv_ok):
    """Test correct reading of systemd properties from helper service.

    The test checks correct values of 'Description' and 'Type' properties
    as these are among the explicitly specified properties. Other properties
    may be present in the extracted dictionary, but their value can vary
    between runs or they can be different based on the specific service.

    Parameters
    ----------
    helper_src_ok : fixture
        Fixture generating a systemd service.
    """

    srv = Service(helper_srv_ok)
    srv.start(blocking=True)
    assert srv.is_active()

    prop_dict = srv._parse_systemd_properties()
    assert prop_dict["Description"] == SERVICE_DESCRIPTION
    assert prop_dict["Type"] == SERVICE_TYPE

    srv.stop(blocking=False)
