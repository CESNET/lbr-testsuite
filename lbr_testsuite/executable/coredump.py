"""
Author(s): Jan Kučera <jan.kucera@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Helper code for collection of core dumps when running child processes.
"""

import os
import shutil
import signal
import resource


class Coredump:
    """
    A class for coredump handling.

    Attributes
    ----------
    _core_limit : int
        The maximum size of the core file (in the units of 'ulimit -c').
    _output_file : str
        File where to write core dump output.
    """

    def __init__(self, inherit=False):
        """
        Helper to start core dumps configuration.

        Parameters
        ----------
        inherit : bool, optional
            Inhering core limit from calling process.
        """

        self._output_file = None
        self._core_limit = resource.RLIM_INFINITY
        if inherit:
            self._core_limit = resource.getrlimit(resource.RLIMIT_CORE)[0]

    def set_output_file(self, file):
        """
        Set output file for core dump.

        Parameters
        ----------
        file : str or pathlib.Path
            Path where to place the core file.
        """

        self._output_file = str(file)

    def get_output_file(self):
        """
        Get core dump output file location.

        Returns
        -------
        str
            Path to a core dump file.
        """

        return self._output_file

    def set_core_limit(self, limit):
        """
        Set the maximum size of the core dump file.

        Parameters
        ----------
        limit : int
            Size as would be given for ulimit -c, use -1 for unlimited.
        """

        if limit < 0:
            self._core_limit = resource.RLIM_INFINITY
        else:
            self._core_limit = int(limit)

    def popen_preexec(self):
        """
        Method to be passed to Popen call to set all ulimit
        configuration. It will be called in the child process just
        before the child is executed.
        """

        core_limit = (self._core_limit, self._core_limit)
        resource.setrlimit(resource.RLIMIT_CORE, core_limit)

    def popen_postexec(self, process):
        """
        Method to be called after the child process exits to rename
        coredump file (if created).

        Parameters
        ----------
        process : subprocess.Popen
            Popen object of the child process terminated.
        """

        if process.returncode != -signal.SIGSEGV:
            return

        if not self._output_file:
            return

        coredump = f'core.{process.pid}'

        if os.path.isfile(coredump):
            shutil.move(coredump, self._output_file)
