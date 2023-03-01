"""
Author(s):
Pavel Krobot <Pavel.Krobot@cesnet.cz>
Kamil Vojanec <vojanec@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

A module providing class for using systemd services.
"""


import logging
import subprocess
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
        self._start_time = None
        self._logger = logging.getLogger(self._name)

    def is_active(self):
        """Check if managed service is currently active.

        Returns
        -------
        bool
            True if service is active, False otherwise.
        """

        # Use "no-exception" to prevent an exception when a service is not active.
        c = executable.Tool(
            ["systemctl", "is-active", self._name], failure_verbosity="no-exception"
        )
        stdout, _ = c.run()
        return stdout.strip() == "active"

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

        if self._start_time is None:
            raise RuntimeError(
                f"Service '{self._name}' has not been started, cannot retrieve return code."
            )
        if self.is_active():
            raise RuntimeError(f"Service '{self._name}' is running, cannot retrieve return code.")

        c = executable.Tool(["systemctl", "show", self._name, "--property", "ExecMainStatus"])
        stdout, _ = c.run()
        out_split = stdout.split("=")

        # Return just the code
        return int(out_split[1])

    def _started(self):
        if self._start_time is not None:
            return self.is_active()

    def _not_started(self):
        return not self._started()

    def _log_failure(self):
        stdout, stderr = self._journalctl_extract_logs()
        self._logger.debug(f"Captured stdout:\n{stdout}")
        self._logger.debug(f"Captured stderr:\n{stderr}")

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
        subprocess.CalledProcessError
            Service failed on startup.
        RuntimeError
            Blocking start timeout expired and service did not start.
        """

        c = executable.Tool(["systemctl", "start", self._name])
        self._start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            c.run()
        except subprocess.CalledProcessError:
            self._log_failure()

        if blocking:
            if not common.wait_until_condition(self._started, self._start_to):
                self._log_failure()
                raise RuntimeError(
                    f"Service {self._name} did not start (waited {self._start_to} seconds)."
                )

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
        subprocess.CalledProcessError
            Service failed when command was issued.
        RuntimeError
            Blocking start timeout expired and service did not stop.
        """

        c = executable.Tool(["systemctl", "stop", self._name])
        try:
            c.run()
        except subprocess.CalledProcessError:
            self._log_failure()

        if blocking:
            if not common.wait_until_condition(self._not_started, self._stop_to):
                self._log_failure()
                raise RuntimeError(
                    f"Service {self._name} did not stop (waited {self._stop_to} seconds)."
                )

    def _journalctl_extract_logs(self):
        c = executable.Tool(["journalctl", "-u", self._name, "--since", self._start_time])
        return c.run()
