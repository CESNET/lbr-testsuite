"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021-2024 CESNET, z.s.p.o.

Implementation of perf profiler.
"""

from ..executable import executable
from .profiler import PidProfiler


class PerfDaemon(executable.Daemon):
    def _handle_failure(self, process_cmd, process_retcode, stdout, stderr):
        """Avoid false-positive reporting. The perf record programs returns
        -2 or -15 when properly terminated.
        """

        if process_retcode != -2 and process_retcode != -15:
            super()._handle_failure(process_cmd, process_retcode, stdout, stderr)
        return stdout, stderr


class AbstractPerf(PidProfiler):
    def __init__(self, data, args=[], logger=None, env=None):
        super().__init__(cmd=self.DEFAULT_CMD, logger=logger, env=env)
        self._data = str(data)
        self._args = args

    def _create_daemon(self, cmd):
        return PerfDaemon(command=cmd, logger=self._logger, env=self._env)


class Perf(AbstractPerf):
    DEFAULT_CMD = ("perf", "record")

    def _build_cmd(self, pid):
        cmd = self._copy_cmd()
        cmd.extend(["-o", self._data, "-p", str(pid), "--all-user"])
        cmd.extend(self._args)
        return cmd


class PerfStat(AbstractPerf):
    DEFAULT_CMD = ("perf", "stat", "record")

    def _build_cmd(self, pid):
        cmd = self._copy_cmd()
        cmd.extend(["-o", self._data, "-p", str(pid)])
        cmd.extend(self._args)
        return cmd


class PerfMem(AbstractPerf):
    DEFAULT_CMD = ("perf", "mem", "record")

    def _build_cmd(self, pid):
        cmd = self._copy_cmd()
        cmd.extend(["--", "-o", self._data, "-p", str(pid), "--all-user"])
        cmd.extend(self._args)
        return cmd


class PerfC2C(AbstractPerf):
    DEFAULT_CMD = ("perf", "c2c", "record")

    def _build_cmd(self, pid):
        cmd = self._copy_cmd()
        cmd.extend(["--", "-o", self._data, "-p", str(pid), "--all-user"])
        cmd.extend(self._args)
        return cmd
