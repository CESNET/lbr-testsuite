"""
Author(s):
Pavel Krobot <Pavel.Krobot@cesnet.cz>
Kamil Vojanec <vojanec@cesnet.cz>
Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

A module providing class for using systemd services.
"""

import logging
import time
from datetime import datetime

from .. import common
from . import executable


class Service:
    """Class representing a systemd service. Allows the service to be started,
    stopped. Also enables access to its activity status and returncode on exit.
    In case of service failure, a journal log is reported.
    """

    def __init__(self, name, start_timeout=5, stop_timeout=5):
        """Create a new service object.

        Parameters
        ----------
        name : str
            Name of service to be managed.
        start_timeout : int
            Number of seconds to wait for the service to start.
        stop_timeout : int
            Number of seconds to wait until service is stopped.
        """

        self._name = name
        self._start_to = start_timeout
        self._stop_to = stop_timeout
        self._last_start_time = self._get_activation_time()
        self._logger = logging.getLogger(self._name)

    def is_active(self, after=None):
        """Check if managed service is currently active.

        after : float, optional
            How many seconds to wait before check. No waiting by
            default.

        Returns
        -------
        bool
            True if service is active, False otherwise.
        """

        # Use "no-exception" to prevent an exception when a service is not active.
        c = executable.Tool(
            ["systemctl", "is-active", self._name], failure_verbosity="no-exception"
        )

        if after:
            time.sleep(after)

        stdout, _ = c.run()
        return stdout.strip() == "active"

    def _parse_systemd_properties(self):
        cmd = [
            "systemctl",
            "show",
            self._name,
        ]

        properties_str, _ = executable.Tool(cmd).run()
        properties_dict = {}

        for prop_line in properties_str.splitlines():
            prop_line_strip = prop_line.strip()
            key, val = prop_line_strip.split("=", maxsplit=1)
            properties_dict[key] = val

        return properties_dict

    def _get_activation_time(self):
        """Obtain the activation time of the service.

        Returns
        -------
        datetime.datetime
            Activation time of managed service.
        """

        if not self.is_active():
            return None

        props = self._parse_systemd_properties()
        timestamp_str = props["ActiveEnterTimestamp"]

        timestamp = datetime.strptime(timestamp_str, "%a %Y-%m-%d %H:%M:%S %Z")
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    def returncode(self):
        """Check the exit return code of the service.

        Returns
        -------
        int
            Service return code.

        Raises
        ------
        RuntimeError
            Service has not been started or is currently running,
            no return code can be retrieved.
        """

        if self._last_start_time is None:
            raise RuntimeError(
                f"Service '{self._name}' has not been started, cannot retrieve return code."
            )
        if self.is_active():
            raise RuntimeError(f"Service '{self._name}' is running, cannot retrieve return code.")

        ec = self._parse_systemd_properties()["ExecMainStatus"]
        return int(ec)

    def _started(self):
        if self._last_start_time is not None:
            return self.is_active()

    def _not_started(self):
        return not self._started()

    def _log_failure(self):
        stdout, stderr = self._journalctl_extract_logs()
        self._logger.debug(f"Captured stdout:\n{stdout}")
        self._logger.debug(f"Captured stderr:\n{stderr}")

    def _run_sysctl_action(self, action):
        assert action in ("start", "stop", "restart", "reload")

        cmd = executable.Tool(["systemctl", action, self._name])
        try:
            cmd.run()
        except executable.ExecutableProcessError:
            self._log_failure()
            raise

    def _start_or_restart(self, blocking, restart=False):
        action = "start" if not restart else "restart"
        self._last_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._run_sysctl_action(action)

        if blocking:
            if not common.wait_until_condition(self._started, self._start_to):
                self._log_failure()
                raise RuntimeError(
                    f"Service {self._name} did not start (waited {self._start_to} seconds)."
                )

    def start(self, blocking=True):
        """Start the service, potentially blocking until it has started.

        Parameters
        ----------
        blocking : bool
            If set to true, this function will wait until the service
            starts, up to a maximum of 'self.start_timeout'.
            Otherwise this function only signals the service to start
            and continues.

        Raises
        ------
        executable.ExecutableProcessError
            Service failed on startup.
        RuntimeError
            Blocking start timeout expired and service did not start.
        """

        self._start_or_restart(blocking)

    def stop(self, blocking=True):
        """Stop the service, potentially blocking until it has stopped.

        Parameters
        ----------
        blocking : bool
            If set to true, this function will wait until the service
            has stopped, up to a maximum of 'self.stop_timeout'.
            Otherwise this function only signals the service to stop
            and continues.

        Raises
        ------
        executable.ExecutableProcessError
            Service failed when command was issued.
        RuntimeError
            Blocking start timeout expired and service did not stop.
        """

        self._run_sysctl_action("stop")

        if blocking:
            if not common.wait_until_condition(self._not_started, self._stop_to):
                self._log_failure()
                raise RuntimeError(
                    f"Service {self._name} did not stop (waited {self._stop_to} seconds)."
                )

    def restart(self, blocking=True):
        """Restart the service, potentially blocking until the restart
        is completed.

        Parameters
        ----------
        blocking : bool
            If set to true, this function will wait until the service
            is restarted, up to a maximum of 'self.stop_timeout'.
            Otherwise this function only signals the service to restart
            and continues.

        Raises
        ------
        executable.ExecutableProcessError
            Service failed when command was issued.
        RuntimeError
            Blocking start timeout expired and service did not stop.
        """

        self._start_or_restart(blocking, restart=True)

    def reload(self):
        """Reload the service.

        Note: Reload completion is rather application specific and it
        cannot be checked here. Thus, there is no "blocking" version.

        Raises
        ------
        executable.ExecutableProcessError
            Service failed when command was issued.
        """

        self._run_sysctl_action("reload")

    def _journalctl_extract_logs(self):
        c = executable.Tool(["journalctl", "-u", self._name, "--since", self._last_start_time])
        return c.run()
