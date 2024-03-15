"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

An executable module providing classes for execution of various tools
(class Tool) and daemons (clas Daemon).
"""

import logging
import pathlib
import signal
import subprocess
import time

from .local_executor import LocalExecutor


class ExecutableException(Exception):
    """Basic exception raised by Executable class"""


class ExecutableProcessError(ExecutableException):
    """Exception raised when process ends with non-zero return code."""

    # Mimic subprocess.CalledProcessError
    def __init__(self, returncode=None, cmd=None):
        self.returncode = returncode
        self.cmd = cmd

    def __str__(self):
        if self.returncode and self.returncode < 0:
            try:
                return "Command '%s' died with %r." % (self.cmd, signal.Signals(-self.returncode))
            except ValueError:
                return "Command '%s' died with unknown signal %d." % (self.cmd, -self.returncode)
        else:
            return "Command '%s' returned non-zero exit status %d." % (self.cmd, self.returncode)


class Executable:
    """Base class for more specific executable subclasses.

    Attributes
    ----------
    DEFAULT_OPTIONS : dict()
        Default options for subprocess.Popen() command. For more
        information about possible options and values see documentation
        of subprocess module. When executing remote commands, executable
        uses fabric module instead of subprocess. However, options should
        behave as close as possible to original subprocess module.
        Current default options:
        - sets capturing of stdout and stderr as text stored within
        subprocess.CompletedProcess.stdout (stdout and stderr is mixed
        together into stdout, since fabric module cannot separate
        outputs under certain conditions),
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
        "stderr": subprocess.STDOUT,
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
        sigterm_ok=False,
        netns=None,
        sudo=False,
        executor=None,
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
        sigterm_ok : bool, optional
            Flag whether it is OK to die with "SIGTERM" return code
            (143 in system, -signal.SIGTERM (-15) in
            subprocess.CalledProcessError.returncode). If set to True,
            a process which exits with code -15 is treated the same as
            if it exits with 0. False by default.
        netns : str, optional
            Network namespace name. If set, a command is executed in
            a namespace using the "ip netns" command. Default "None".
        sudo : bool, optional
            Force command to run with sudo.
        executor : executable.Executor, optional
            Executor to use. If not set, use local executor (run
            commands on local machine).
        """

        assert failure_verbosity in self.FAILURE_VERBOSITY_LEVELS

        self._options = self.DEFAULT_OPTIONS.copy()
        self._output_files = dict(stdout=None, stderr=None)
        self._input_file = None
        self._sigterm_ok = sigterm_ok
        self._post_exec_fn = None
        self._netns = netns
        self._sudo = sudo

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
            self._options["env"] = None

        if executor is not None:
            self._executor = executor
            assert not self._executor.is_running(), "Executor contains unfinished process"
            self._executor.reset_process()
        else:
            self._executor = LocalExecutor()

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

        if self._options["env"] is None:
            self._options["env"] = {}

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

        Raises
        ------
        RuntimeError
            When trying to use strace on remote execution.
        """

        if not isinstance(self._executor, LocalExecutor):
            raise RuntimeError("Strace is supported only for local execution")

        self._cmd = strace.wrap_command(self._cmd)

    def set_coredump(self, coredump):
        """Enable creation of core dump for a command.

        Parameters
        ----------
        coredump : :class:`Coredump`
            Configured instance of Coredump class.

        Raises
        ------
        RuntimeError
            When trying to use core dump on remote execution.
        """

        if not isinstance(self._executor, LocalExecutor):
            raise RuntimeError("Core dump is supported only for local execution")

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
            local log file. Otherwise the argument value follow rules of the
            subprocess module.
        stderr : str, pathlib.Path, int or subprocess special value, optional
            Setting stderr is allowed only in local execution - only
            exception is when setting subprocess.STDOUT.
            If argument is a string, it is assumed that it is path to a
            local log file. Otherwise the argument value follow rules of the
            subprocess module.

        Raises
        ------
        RuntimeError
            When trying to set stderr output on remote execution.
        """

        self._set_output("stdout", stdout)
        if stderr is None or stderr == subprocess.STDOUT:
            self._options["stderr"] = subprocess.STDOUT
        else:
            if not isinstance(self._executor, LocalExecutor):
                raise RuntimeError("Setting stderr output is supported only in local execution")

            self._set_output("stderr", stderr)

    def set_input(self, command_input):
        """Set input for a command.

        Parameters
        ----------
        command_input : str, pathlib.Path, int or subprocess special
            value. If argument is a string, it is assumed that it is
            a path to a local input file. Otherwise the argument value
            follows the rules of the subprocess module.
        """

        if not isinstance(self._executor, LocalExecutor):
            raise RuntimeError("Setting stdin is supported only in local execution")

        if isinstance(command_input, pathlib.Path):
            command_input = str(command_input)

        if isinstance(command_input, str):
            self._options["stdin"] = open(command_input, "r")
            self._input_file = self._options["stdin"]
            self._logger.info(f"stdin for command {self._cmd_str()} set to: {command_input}.")
        else:
            self._options["stdin"] = command_input

    def _close_io_files(self):
        """Close input/output files opened within setting
        of input/outputs.
        """

        for f in self._output_files.values():
            if f is not None:
                f.close()

        if self._input_file is not None:
            self._input_file.close()

    def _handle_failure(self, process_cmd, process_retcode, stdout, stderr):
        """Handle failure of a command.

        If command is allowed to fail, only debug message is printed.
        Otherwise command output together with errro is printed and
        an exception is reraised.
        """

        if self._sigterm_ok and process_retcode == -signal.SIGTERM:
            return

        if self._failure_verbosity == "silent":
            return

        fail_msg = f'Command "{process_cmd}" has failed with code {process_retcode}.'

        if self._failure_verbosity == "normal":
            self._logger.error(fail_msg)
            self._logger.error(f"Captured stdout:\n{stdout}")
            self._logger.error(f"Captured stderr:\n{stderr}")
        else:
            assert (
                self._failure_verbosity == "no-error" or self._failure_verbosity == "no-exception"
            )
            self._logger.debug(fail_msg)
            self._logger.debug(f"Captured stdout:\n{stdout}")
            self._logger.debug(f"Captured stderr:\n{stderr}")

        if self._failure_verbosity == "normal" or self._failure_verbosity == "no-error":
            raise ExecutableProcessError(process_retcode, process_cmd)

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
        self._close_io_files()
        if self._executor.get_process() is not None:
            self._executor.wait()
            if self._post_exec_fn is not None:
                self._post_exec_fn(self._executor.get_process())

    def _start(self):
        try:
            self._executor.run(
                self._cmd,
                netns=self._netns,
                sudo=self._sudo,
                **self._options,
            )
        except Exception:
            self._finalize()
            raise

    def _standardize_outputs(self, stdout, stderr):
        """Unify outputs between local and remote executor.

        This, however, means that distinction between
        empty output ("") and NO output (None) is lost.
        """

        if stdout is None:
            stdout = ""
        if stderr is None:
            stderr = ""

        if not isinstance(self._executor, LocalExecutor):
            # If output is redirected to file, stdout/err should be empty.
            # But in remote executor, output is still captured:
            #
            # "As such, all output will appear on out_stream and
            # be captured into the stdout result attribute"
            # See https://docs.pyinvoke.org/en/latest/api/runners.html#invoke.runners.Runner.run.command
            for k, v in self._output_files.items():
                if v is not None:
                    if k == "stdout":
                        stdout = ""
                    if k == "stderr":
                        stderr = ""

        return (stdout, stderr)

    def _wait_or_kill(self, timeout):
        stdout, stderr = self._executor.wait_or_kill(timeout)
        stdout, stderr = self._standardize_outputs(stdout, stderr)
        self._finalize()

        status = self._executor.get_termination_status()
        if status["rc"] != 0:
            self._handle_failure(status["cmd"], status["rc"], stdout, stderr)

        return stdout, stderr

    def returncode(self):
        """Get return code of an executable.

        Returns
        -------
        int
            Return-code or "None" if an executable was not started
            or did not finish yet.
        """

        if self._executor.get_process() is None or self._executor.is_running():
            return None

        status = self._executor.get_termination_status()

        return status["rc"]


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
            A pair composed from stdout and stderr.
        """

        self._executor.reset_process()
        self._start()
        return self._wait_or_kill(timeout)


class AsyncTool(Executable):
    """Class for command execution.

    This class is used for asynchronous one-shot commands. A command is started
    and then user awaits result with wait_or_kill method. Stdout and stderr could
    be read continuously while the command is running.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stdout, self._stderr = None, None
        self._terminated = None

    def run(self):
        """Run the command. Start and don't wait for completion."""

        if self._executor.get_process() is not None and not self._terminated:
            raise RuntimeError("start called on a started process")

        self._executor.reset_process()
        self._start()
        self._stdout, self._stderr = self._executor.get_output_iterators()
        self._terminated = False

    def is_running(self, after=None):
        """Check whether process is running.

        after : float, optional
            How many seconds to wait before check. No waiting by
            default. The waiting operation blocks execution.

        Returns
        -------
        bool
            True if the process is running, False otherwise.
        """

        if self._executor.get_process() is None:
            return False

        if after:
            time.sleep(after)

        return self._executor.is_running()

    def wait_or_kill(self, timeout=None):
        """Wait for command to terminate.

        When timeout is not None, process is killed if it does not
        terminate after timeout in seconds.

        Parameters
        ----------
        timeout : int, optional
            Timeout in seconds after that is process killed.
            Note: depending on the implementation of the executor,
            None value may not mean an infinite wait for the process
            to complete, but a very long timeout (hundreds of hours).

        Returns
        -------
        tuple
            A pair composed from stdout and stderr.
        """

        if self._executor.get_process() is None:
            return ("", "")

        if self._terminated:
            stdout, stderr = self._executor.wait_or_kill(1)
            stdout, stderr = self._standardize_outputs(stdout, stderr)
            return (stdout, stderr)

        return self._wait_or_kill(timeout)

    @property
    def stdout(self):
        """Get iterator for continuous read of stdout while process is running.

        Note: each line which is read by iterator is removed from the final
        output (wait_or_kill method).

        Returns
        -------
        OutputIterator
            Stdout iterator object.

        Raises
        ------
        RuntimeError
            When process is not running or stdout is redirected to file.
        """

        if self._output_files.get("stdout", None) is not None:
            raise RuntimeError("Cannot read output which is redirected to file.")

        if not self.is_running():
            raise RuntimeError("Output can be continuously read only while the process is running.")

        return self._stdout

    @property
    def stderr(self):
        """Get iterator for continuous read of stderr while process is running.

        Note: each line which is read by iterator is removed from the final
        output (wait_or_kill method).

        Returns
        -------
        OutputIterator
            Stderr iterator object.

        Raises
        ------
        RuntimeError
            When process is not running or stderr is redirected to file.
        """

        if self._output_files.get("stderr", None) is not None:
            raise RuntimeError("Cannot read output which is redirected to file.")

        if not self.is_running():
            raise RuntimeError("Output can be continuously read only while the process is running.")

        return self._stderr

    def _finalize(self):
        super()._finalize()
        self._terminated = True


class Daemon(Executable):
    """Class for execution of a command as a daemon.

    This class is used to start command on background.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminated = None

    def _terminate(self):
        self._executor.terminate()

    def _finalize(self):
        super()._finalize()
        self._terminated = True

    def start(self):
        """Start the command on background.

        Returns
        -------
        tuple or None
            A pair composed from stdout and stderr
            if start fails. Implicit None otherwise.
        """

        if self._executor.get_process() is not None and not self._terminated:
            raise RuntimeError("start called on a started process")

        self._executor.reset_process()
        self._start()

        if not self.is_running():
            return self.stop()

        self._terminated = False

    def stop(self, timeout=30):
        """Stop previously started command and retrieve its
        outputs (stdout and stderr). If the command has been terminated
        retrieve outputs only.

        Parameters
        ----------
        timeout : int
            Time for command to terminate. If command does not terminate
            within this timeout, it is killed.

        Returns
        -------
        tuple
            A pair composed from stdout and stderr.
        """

        if self._executor.get_process() is None:
            return

        if self._terminated:
            stdout, stderr = self._executor.wait_or_kill(1)
            stdout, stderr = self._standardize_outputs(stdout, stderr)
            return (stdout, stderr)

        self._terminate()
        return self._wait_or_kill(timeout)

    def is_running(self, after=None):
        """Check whether a daemon process is running.

        after : float, optional
            How many seconds to wait before check. No waiting by
            default. The waiting operation blocks execution.

        Returns
        -------
        bool
            True if the process is running, False otherwise.
        """

        if self._executor.get_process() is None or self._terminated:
            return False

        if after:
            time.sleep(after)

        return self._executor.is_running()
