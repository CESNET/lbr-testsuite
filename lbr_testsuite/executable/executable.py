"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

An executable module providing classes for execution of various tools
(class Tool) and daemons (clas Daemon).
"""

import logging
import os
import pathlib
import subprocess


class Executable:
    """Base class for more specific executable subclasses.

    Attributes
    ----------
    DEFAULT_OPTIONS : dict()
        Default options for subprocess.Popen() command. For more
        information about possible options and values see documentation
        of subprocess module.
        Current default options:
        - sets capturing of stdout and stderr as text stored within
        subprocess.CompletedProcess.stdout/.stderr,
        - does not allow execution commands as strings. However, this
        option is changed automatically when the string command is
        requested upon construction.
        - sets no timeout,
        - return code within subprocess.CompletedProcess.returncode is
        tested and in the case of non-zero return code an exception is
        raised.
    FAILURE_VERBOSITY_LEVELS: tuple()
        Failure verbosity levels controls how will an executable acts on
        a failure:
        - normal: fails in a normal way. An error is printed and
        an exception is raised when an executable fails.
        - no-error: does not produce an error (error messages are printed
        only as a debug), rest is as same as on 'normal' level.
        - no-exception: does not raise an exception on executable failure,
        rest is as same as on 'no-error' level.
        - silent: a failure does not provide any output nor raises
        an exception.
    """

    DEFAULT_OPTIONS = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "encoding": "utf-8",
        "shell": False,
        "start_new_session": True,  # This runs the subprocess in a new session,
        # so it is not directly affected by pressing CTRL+C which basically sends
        # SIGINT to all processes within the process group. We can thus catch and
        # process KeyboardInterrupt properly and kill the subprocess afterwards.
    }

    FAILURE_VERBOSITY_LEVELS = ("normal", "no-error", "no-exception", "silent")

    def __init__(
        self,
        command,
        logger=None,
        default_logger_level=None,
        failure_verbosity="normal",
        env=None,
    ):
        """
        Parameters
        ----------
        command : str, list or tuple
            Command in a form of string or as a tuple / list where items
            are command and its arguments. If command is set as a string,
            'shell' option is set to True. As for subprocess module,
            command and its arguments in a form of list are prefered.
        logger : logging.Logger(), optional
            Instance of logging.Logger class. If not set, default global
            logger is used.
        default_logger_level : int
            Logging value of default logger. Value is logging level as
            defined by logging library. Setting this argument has no
            effect if custom logger is passed via logger argument.
        failure_verbosity : str
            Failure verbosity control. See FAILURE_VERBOSITY_LEVELS
            description.
        env : dict(), deprecated
            Mapping that defines the environment variables for the new
            process. For more information, see official documentation
            of subprocess module. This option is deprecated and will
            be removed in next major version. To set environment
            variables use *_env methods.
        """

        assert failure_verbosity in self.FAILURE_VERBOSITY_LEVELS

        self._process = None
        self._options = self.DEFAULT_OPTIONS.copy()
        self._output_files = dict(stdout=None, stderr=None)
        self._post_exec_fn = None

        if isinstance(command, str):
            self._options["shell"] = True
            self._cmd = command
        elif isinstance(command, tuple) or isinstance(command, list):
            self._cmd = list(command)  # always get list because of append_arguments method
        else:
            assert False, f"Unsupported command type {type(command)}."

        if logger is not None:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)
            if default_logger_level is not None:
                self._logger.setLevel(default_logger_level)

        self._failure_verbosity = failure_verbosity
        if env is not None:
            self._options["env"] = env
        else:
            self._options["env"] = os.environ.copy()

    def _cmd_str(self):
        """Convert command to string representation."""

        if isinstance(self._cmd, str):
            return self._cmd
        else:
            assert isinstance(self._cmd, list)
            return " ".join(self._cmd)

    def set_failure_verbosity(self, failure_verbosity):
        """Set failure verbosity. See FAILURE_VERBOSITY_LEVELS
        description.

        Parameters
        ----------
        failure_verbosity : str
            Failure verbosity value.
        """

        assert failure_verbosity in self.FAILURE_VERBOSITY_LEVELS

        self._failure_verbosity = failure_verbosity

    def set_env(self, env):
        """Set an environment.

        Parameters
        ----------
        env : dict
            Mapping that defines the environment variables.
        """

        self._options["env"] = env

    def set_env_key(self, key, value):
        """Set new environment variable mapping.

        Parameters
        ----------
        key : str
            Key value of the variable.
        value : str
            Value of the varible.
        """

        self._options["env"][key] = value

    def clear_env(self):
        """Clear all environment variables mapping."""

        self._options["env"] = {}

    def set_cwd(self, path):
        """Set working directory for a command.

        Parameters
        ----------
        path : str or pathlib.Path
            Path to the working directory. Directory is not created if
            it does not exist.
        """

        self._options["cwd"] = path

    def set_strace(self, strace):
        """Set strace for a command.

        Parameters
        ----------
        strace : :class:`Strace`
            Configured instance of Strace class.
        """

        self._cmd = strace.wrap_command(self._cmd)

    def set_coredump(self, coredump):
        """Enable creation of core dump for a command.

        Parameters
        ----------
        coredump : :class:`Coredump`
            Configured instance of Coredump class.
        """

        self._options["preexec_fn"] = coredump.popen_preexec
        self._post_exec_fn = coredump.popen_postexec

    def _set_output(self, output_type, output):
        """Set output for a command (stdout or stderr)."""

        assert output_type in ["stdout", "stderr"]

        if isinstance(output, pathlib.Path):
            output = str(output)

        if isinstance(output, str):
            self._options[output_type] = open(output, "w")
            self._output_files[output_type] = self._options[output_type]
            self._logger.info(f"{output_type} for command {self._cmd_str()} set to: {output}.")
        else:
            self._options[output_type] = output

    def set_outputs(self, stdout, stderr=None):
        """Set outputs for a command.

        If no specific stderr is requested, it is set to stdout.

        Parameters
        ----------
        stdout : str, pathlib.Path, int or subprocess special value
            If argument is a string, it is assumed that it is path to a
            log file. Otherwise the argument value follow rules of the
            subprocess module.
        stderr : str, pathlib.Path, int or subprocess special value, optional
            If argument is a string, it is assumed that it is path to a
            log file. Otherwise the argument value follow rules of the
            subprocess module.
        """

        self._set_output("stdout", stdout)
        if stderr is None:
            self._options["stderr"] = subprocess.STDOUT
        else:
            self._set_output("stderr", stderr)

    def _close_output_files(self):
        """Close output files opened withing setting of outputs."""

        for f in self._output_files.values():
            if f is not None:
                f.close()

    def _handle_failure(self, process_error, stdout, stderr):
        """Handle failure of a command.

        If command is allowed to fail, only debug message is printed.
        Otherwise command output together with errro is printed and
        an exception is reraised.
        """

        if self._failure_verbosity == "silent":
            return

        fail_msg = f'Command "{process_error.cmd}" has failed with code {process_error.returncode}.'

        if self._failure_verbosity == "normal":
            self._logger.error(fail_msg)
        else:
            assert (
                self._failure_verbosity == "no-error" or self._failure_verbosity == "no-exception"
            )
            self._logger.debug(fail_msg)

        self._logger.debug(f"Captured stdout:\n{stdout}")
        self._logger.debug(f"Captured stderr:\n{stderr}")

        if self._failure_verbosity == "normal" or self._failure_verbosity == "no-error":
            raise

    def append_arguments(self, args):
        """Append arguments to a command.

        Parameters
        ----------
        args : str or list(str)
            Arguments to append to the command. If command as a string
            is used, the value of this argument has to be also string.
            Otherwise argument can be string or list. If string is used
            it is assumed that it is a single argument.
        """

        if isinstance(self._cmd, str):
            assert isinstance(args, str)
            self._cmd = self._cmd + " " + args  # single argument expected
        else:
            assert isinstance(self._cmd, list)
            if isinstance(args, str):
                args = [args]
            self._cmd.extend(args)

    def _finalize(self):
        self._close_output_files()
        if self._process is not None:
            self._process.wait()
            if self._post_exec_fn is not None:
                self._post_exec_fn(self._process)

    def _start(self):
        try:
            self._process = subprocess.Popen(self._cmd, **self._options)
        except Exception:
            self._finalize()
            raise

    def _wait_or_kill(self, timeout):
        try:
            """Note from subprocess documentation:
            This will deadlock when using stdout=PIPE or stderr=PIPE
            and the child process generates enough output to a pipe
            such that it blocks waiting for the OS pipe buffer to accept
            more data. Use Popen.communicate() when using pipes to
            avoid that.
            """
            stdout, stderr = self._process.communicate(timeout)
        except subprocess.TimeoutExpired:
            self._process.kill()
            stdout, stderr = self._process.communicate()
        finally:
            self._finalize()

            try:
                subprocess.CompletedProcess.check_returncode(self._process)
            except subprocess.CalledProcessError as ee:
                self._handle_failure(ee, stdout, stderr)

        return stdout, stderr


class Tool(Executable):
    """Class for command execution.

    This class is used for one-shot commands.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, timeout=None):
        """Run the command and wait for it to complete. If the command
        does not finish within the given timeout, it is terminated.

        Parameters
        ----------
        timeout : int
            Time for command to execute and finish.

        Returns
        -------
        tuple
            A pair composed from stdout and stderr acquired using
            subprocess.communicate() method.
        """

        self._start()
        return self._wait_or_kill(timeout)


class Daemon(Executable):
    """Class for execution of a command as a daemon.

    This class is used to start command on background.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminated = False

    def _terminate(self):
        self._process.terminate()

    def _finalize(self):
        super()._finalize()
        self._terminated = True

    def start(self):
        """Start the command on background.

        Returns
        -------
        tuple or None
            A pair composed from stdout and stderr acquired using
            subprocess.communicate() method if start fails. Implicit
            None otherwise.
        """

        if self._process is not None and not self._terminated:
            raise RuntimeError("start called on a started process")

        self._start()

        if not self.is_running():
            return self.stop()

        self._terminated = False

    def stop(self, timeout=30):
        """Stop previously started command.

        Parameters
        ----------
        timeout : int
            Time for command to terminate. If command does not terminate
            within this timeout, it is killed.

        Returns
        -------
        tuple
            A pair composed from stdout and stderr acquired using
            subprocess.communicate() method.
        """

        if self._process is None or self._terminated:
            return

        self._terminate()
        return self._wait_or_kill(timeout)

    def is_running(self):
        """Check whether a daemon process is running.

        Returns
        -------
        bool
            True if the process is running, False otherwise.
        """

        if self._process is None or self._terminated:
            return False

        return self._process.poll() is None
