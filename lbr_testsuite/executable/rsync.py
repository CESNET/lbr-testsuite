"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Data synchronization tool.

Synchronization can be done between directories on
local machine or between local and remote machine.
"""

import logging
import os
from pathlib import Path
from shlex import quote

from .. import common
from .executable import ExecutableProcessError, Tool
from .local_executor import LocalExecutor


class RsyncException(Exception):
    """Basic exception raised by Rsync class."""


class Rsync:
    """Implement data synchronization.

    Synchronization can be done between directories on
    local machine or between local and remote machine.

    Parameters
    ----------
    executor : executable.Executor, optional
        Executor to use. If not set, use local executor (run
        commands on local machine).
    data_dir : str, optional
        Data directory on host.
        Host can be local or remote.
        Files pushed (uploaded) to host will be in
        this directory.
        If not set, temporary directory is created.
        Temporary directory is reused during single
        session (per-host and per-user, meaning each
        user has own directory on each different host).
        By default, this means that synchronized files
        can be shared by multiple tests in one session.

        Warning: method wipe_data_directory() removes
        everything inside this directory, so
        don't use home directory or cwd (~ or .) etc.

    Raises
    ------
    RsyncException
        Could not prepare temporary directory.
    """

    # Session-based temporary storage (per-host and per-user)
    STORAGES = {}

    def __init__(
        self,
        executor=LocalExecutor(),
        data_dir=None,
    ):
        self._executor = executor

        if data_dir is not None:
            self._data_dir = data_dir
        else:
            user = common.get_real_user()

            host = executor.get_host()

            if host not in self.STORAGES:
                self.STORAGES[host] = {}

            if user not in self.STORAGES[host]:
                try:
                    stdout, _ = Tool(["mktemp", "-d"], executor=executor).run()
                    stdout = stdout.strip()
                    self.STORAGES[host][user] = stdout

                    if os.geteuid() == 0:
                        # If running under root, created directory would
                        # have root-only permissions.
                        # Since connection to host is under non-root username,
                        # user would not have access to this directory.
                        # Keep root group for root access.
                        Tool(["chown", "--silent", user, stdout], executor=executor).run()
                except ExecutableProcessError as err:
                    raise RsyncException(
                        f"Could not prepare temporary directory, err: {err}"
                    ) from err

            self._data_dir = self.STORAGES[host][user]
            logging.getLogger().debug(f"Rsync: using directory {self._data_dir} on host {host}")

    def get_data_directory(self):
        """Get data directory.

        Returns
        -------
        str
            Path of data directory.
        """

        return self._data_dir

    def remove_path(self, target):
        """Remove file or directory in data directory.

        Parameters
        ----------
        target : str
            File or directory in data directory to remove.
            If it's relative path, assume it's relative to
            data directory.

        Raises
        ------
        RsyncException
            Data directory is not in path or target could not be deleted.
        """

        try:
            target = self._resolve_data_dir_path(target)
        except ValueError as err:
            raise RsyncException(
                f"Can't remove a path outside the data directory {self._data_dir}"
            ) from err

        try:
            Tool(["rm", "-rf", target], executor=self._executor).run()
        except ExecutableProcessError as err:
            raise RsyncException(
                f"Could not delete file or directory {target}, err: {err}"
            ) from err

    def wipe_data_directory(self):
        """Remove all files and directories in data directory.

        Raises
        ------
        RsyncException
            Could not wipe data directory.
        """

        # Set command in string to enable execution via shell.
        # subprocess/Popen doesn't expand "/*" like shell.
        try:
            Tool(f"rm -rf {self._data_dir}/*", executor=self._executor).run()
        except ExecutableProcessError as err:
            raise RsyncException(f"Could not wipe data directory, err: {err}") from err

    def create_file(self, name, content=""):
        """Create new file.

        Parameters
        ----------
        name : str
            Name of a file. File extension should be included.
        content : str, optional
            Content to be inserted into file. Content is escaped
            with shlex.quote().

        Returns
        -------
        str
            Path to created file.

        Raises
        ------
        RsyncException
            Could not create file or could not write content to file.
        """

        file = Path(self._data_dir) / name

        try:
            Tool(
                f"touch {file}",
                executor=self._executor,
            ).run()
        except ExecutableProcessError as err:
            raise RsyncException(f"Could not create file {name}, err: {err}") from err

        if content:
            try:
                Tool(
                    f"echo {quote(content)} > {file}",
                    executor=self._executor,
                ).run()
            except ExecutableProcessError as err:
                raise RsyncException(f"Could not write to file {name}, err: {err}") from err

        return str(file)

    def push_path(self, source, checksum_diff=True):
        """Push file or directory to data directory on host.

        If host is remote, use 'rsync' tool.
        If localhost, use 'cp' tool.

        Parameters
        ----------
        source : str
            File or directory to push.
        checksum_diff : bool, optional
            Relevant only if host is remote.
            By default, source is not pushed if file/directory
            already exists and has same checksum. If set to
            False, compare files by mod-time and size. It's
            not as accurate as checksum, but it's faster.
            For more info see rsync manpage:
            https://linux.die.net/man/1/rsync

        Returns
        -------
        str
            Path to pushed file or directory.

        Raises
        ------
        RsyncException
            Could not push file.
        """

        try:
            if isinstance(self._executor, LocalExecutor):
                Tool(["cp", "--recursive", source, self._data_dir]).run()
            else:
                cmd = self._prepare_for_filesync(checksum_diff)
                conn = self._executor.get_connection()

                # Set command in string to enable execution via shell.
                # cmd['sshpass'] can be empty if password is not used.
                # subprocess/Popen does not accept empty arguments.
                Tool(
                    f"{cmd['sshpass']} rsync {cmd['checksum']} --recursive {cmd['rsh']} "
                    f"{source} {conn.user}@{conn.host}:{self._data_dir}",
                ).run()

        except ExecutableProcessError as err:
            raise RsyncException(f"Couldn't push {source}, error: {err}") from err

        return str(Path(self._data_dir) / Path(source).name)

    def pull_path(self, source, destination="."):
        """Pull file or directory from data directory.

        If host is remote, use 'rsync' tool.
        If localhost, use 'cp' tool.

        Parameters
        ----------
        source : str
            File or directory in data directory to pull from host.
            Path can be relative or absolute.
        destination: str, optional
            Local directory to store downloaded content.

        Returns
        -------
        str
            Path to pulled file or directory.

        Raises
        ------
        RsyncException
            Local directory does not exist or could not be created.
            Could not pull file.
        """

        try:
            source = self._resolve_data_dir_path(source)
        except ValueError as err:
            raise RsyncException(
                f"Can't pull a path outside the data directory {self._data_dir}"
            ) from err

        if isinstance(self._executor, LocalExecutor):
            try:
                Tool(["cp", "--recursive", source, destination]).run()
            except ExecutableProcessError as err:
                raise RsyncException(f"Couldn't pull {source}, error: {err}") from err
        else:
            cmd = self._prepare_for_filesync()
            conn = self._executor.get_connection()

            try:
                Path(destination).mkdir(parents=True, exist_ok=True)
            except OSError as err:
                raise RsyncException(
                    f"Couldn't create local directory {destination}, error: {err}"
                ) from err

            try:
                default_owner = None

                if os.geteuid() == 0:
                    default_owner, _ = Tool(
                        ["stat", "--dereference", "--format=%U", source],
                        executor=self._executor,
                    ).run()
                    default_owner = default_owner.strip()  # remove \n

                    # Source could be created when command was under root.
                    # Change ownership of source so it can be pulled
                    # by regular user via rsync.
                    Tool(
                        ["chown", "--silent", "--recursive", conn.user, source],
                        executor=self._executor,
                    ).run()

                # Set command in string to enable execution via shell.
                # cmd['sshpass'] can be empty if password is not used.
                # subprocess/Popen does not accept empty arguments.
                Tool(
                    f"{cmd['sshpass']} rsync --recursive {cmd['rsh']} "
                    f"{conn.user}@{conn.host}:{source} {destination}",
                ).run()

            except ExecutableProcessError as err:
                raise RsyncException(f"Couldn't pull {source}, error: {err}") from err
            finally:
                if default_owner:
                    Tool(
                        ["chown", "--silent", default_owner, source],
                        executor=self._executor,
                    ).run()

        return str(Path(destination) / Path(source).name)

    def _prepare_for_filesync(self, checksum_diff=False):
        """Prepare connection details (password, key and checksum)
        to be passed to a rsync instance for pull and push methods.
        """

        checksum = "--checksum" if checksum_diff else ""
        sshpass = ""
        rsh = ""
        connect_kwargs = self._executor.get_connection().connect_kwargs

        # rsync doesn't support SSH login via password, thus
        # sshpass is used to provide password automatically
        if "password" in connect_kwargs:
            try:
                Tool("command -v sshpass").run()
            except ExecutableProcessError as err:
                raise RsyncException("sshpass binary is missing") from err

            sshpass = f"sshpass -p {connect_kwargs['password']}"

        # Provide SSH key to rsync via --rsh (remote-shell) parameter
        if "key_filename" in connect_kwargs and "password" not in connect_kwargs:
            key = connect_kwargs["key_filename"][0]
            rsh = f"--rsh='ssh -i {key}'"

        connection_details = {"sshpass": sshpass, "checksum": checksum, "rsh": rsh}

        return connection_details

    def _resolve_data_dir_path(self, path):
        """Resolve relative path and verify that it is inside the data directory."""

        path = Path(path)
        path = Path(self._data_dir) / path if not path.is_absolute() else path
        path = path.resolve()

        if Path(self._data_dir) not in path.parents:
            raise ValueError

        return str(path)
