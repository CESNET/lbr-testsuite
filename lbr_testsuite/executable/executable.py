"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

An executable module providing classes for execution of various tools
(class Tool) and daemons (clas Daemon).
"""

import logging
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
    """

    DEFAULT_OPTIONS = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'encoding': 'utf-8',
        'shell': False,
        'start_new_session': True,  # This runs the subprocess in a new session,
        # so it is not directly affected by pressing CTRL+C which basically sends
        # SIGINT to all processes within the process group. We can thus catch and
        # process KeyboardInterrupt properly and kill the subprocess afterwards.
    }

    def __init__(
        self,
        command,
        logger=None,
        default_logger_level=None,
        allow_to_fail=False,
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
        allow_to_fail : bool
            Flag whether the command is allowed to end with an error.
            When a command is not allowed to fail, an error is printed
            and an exception is raised. If command is allowed to fail,
            the error is printed only as a debug message and no
            exception is raised.
        env : dict()
            Mapping that defines the environment variables for the new
            process. For more information, see official documentation
            of subprocess module.
        """

        self._process = None
        self._options = self.DEFAULT_OPTIONS.copy()
        self._output_files = dict(stdout=None, stderr=None)
        self._post_exec_fn = None

        if isinstance(command, str):
            self._options['shell'] = True
            self._cmd = command
        elif isinstance(command, tuple) or isinstance(command, list):
            self._cmd = list(command)  # always get list because of append_arguments method
        else:
            assert False, f'Unsupported command type {type(command)}.'

        if logger is not None:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)
            if default_logger_level is not None:
                self._logger.setLevel(default_logger_level)

        self._allow_to_fail = allow_to_fail
        self._options['env'] = env

    def _cmd_str(self):
        """Convert command to string representation.
        """

        if isinstance(self._cmd, str):
            return self._cmd
        else:
            assert isinstance(self._cmd, list)
            return " ".join(self._cmd)

    def set_strace(self, strace):
        """Set strace for a command.

        Parameters
        ----------
        strace : Strace()
            Configured instance of Strace class.
        """

        self._cmd = strace.wrap_command(self._cmd)

    def set_coredump(self, coredump):
        """Enable creation of core dump for a command.

        Parameters
        ----------
        coredump : Coredump()
            Configured instance of Coredump class.
        """

        self._options['preexec_fn'] = coredump.popen_preexec
        self._post_exec_fn = coredump.popen_postexec

    def _set_output(self, output_type, output):
        """Set output for a command (stdout or stderr).
        """

        assert output_type in ['stdout', 'stderr']

        if isinstance(output, pathlib.Path):
            output = str(output)

        if isinstance(output, str):
            self._options[output_type] = open(output, 'w')
            self._output_files[output_type] = self._options[output_type]
            self._logger.info(
                f'{output_type} for command {self._cmd_str()} set to: {output}.'
            )
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

        self._set_output('stdout', stdout)
        if stderr is None:
            self._options['stderr'] = subprocess.STDOUT
        else:
            self._set_output('stderr', stderr)

    def _close_output_files(self):
        """Close output files opened withing setting of outputs.
        """

        for f in self._output_files.values():
            if f is not None:
                f.close()

    def _handle_failure(self, process_error, stdout, stderr):
        """Handle failure of a command.

        If command is allowed to fail, only debug message is printed.
        Otherwise command output together with errro is printed and
        an exception is reraised.
        """

        fail_msg = f'Command "{process_error.cmd}" has failed with code {process_error.returncode}.'

        if self._allow_to_fail:
            self._logger.debug(f'{fail_msg}. This failure is allowed.')
        else:
            self._logger.error(fail_msg)
            self._logger.debug(f'Captured stdout:\n{stdout}')
            self._logger.debug(f'Captured stderr:\n{stderr}')
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
            self._cmd = self._cmd + ' ' + args  # single argument expected
        else:
            assert isinstance(self._cmd, list)
            if isinstance(args, str):
                args = [args]
            self._cmd.extend(args)

    def _finalize(self):
        self._close_output_files()
        if self._post_exec_fn is not None:
            self._post_exec_fn(self._process)

    def _start(self):
        try:
            self._process = subprocess.Popen(self._cmd, **self._options)
        finally:
            self._finalize()

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

    def start(self):
        """Start the command on background.
        """

        if self._process is not None:
            raise RuntimeError('start called on a started process')

        self._start()

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

        if self._process is None:
            return

        self._process.terminate()
        return self._wait_or_kill(timeout)

    def is_running(self):
        """Check whether a daemon process is running.

        Returns
        -------
        bool
            True if the process is running, False otherwise.
        """

        if self._process is None:
            return False

        return self._process.poll() is None