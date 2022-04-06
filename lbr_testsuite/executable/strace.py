"""
Author(s): Jan Viktorin <viktorin@cesnet.cz>

Copyright: (C) 2021 CESNET, z.s.p.o.

Helper code for strace invocation.
"""


class Strace:
    """
    A class for strace usage.

    Attributes
    ----------
    _output_file : str
        File where to write strace output.
    _expr : set(str)
        Set of expressions to be added to the strace call via '-e'
        argument of strace tool.
    _args : tuple(str)
        Tuple of arguments to be always passed to the strace call.
    """

    def __init__(self):
        self._output_file = None
        self._expr = set()
        self._args = (
            "-DDD",  # avoid killing strace too early
            "-C",  # include syscalls summary on exit
            "-i",  # print instruction pointer
            "-f",  # follow forks
            "-tt",  # include absolute timestamps with us
            "-T",  # time spent in system calls
            "-y",  # print paths to file descriptors
        )

    def add_expression(self, expr):
        """
        Add expression to be used by strace. See -e option in strace(1).

        Parameters
        ----------
        expr : str or tuple
            Expression (or tuple of expressions) as would be given for -e option to strace.
        """

        if isinstance(expr, tuple):
            for e in expr:
                self._expr.add(e)
        else:
            assert isinstance(expr, str), "argument has to be string or tuple"
            self._expr.add(expr)

    def set_output_file(self, file):
        """
        Set output file for strace reporting.

        Parameters
        ----------
        file : str or pathlib.Path
            File as would be given for -o option to strace.
        """

        self._output_file = str(file)

    def get_output_file(self):
        """
        Get strace output file location.

        Returns
        -------
        str
            Path to a strace output file.
        """

        return self._output_file

    def _get_args(self):
        """
        Get all arguments that would be passed to strace.

        Returns
        -------
        list(str)
            List of arguments for strace command.
        """

        args = list(self._args)

        if self._output_file is not None:
            args.append("-o")  # redirect strace to file
            args.append(self._output_file)

        if self._expr:
            args.append("-e")
            trace_expr = ""
            for expr in self._expr:
                trace_expr = f"{trace_expr}{expr},"
            trace_expr = trace_expr[:-1]  # Remove last comma
            args.append(trace_expr)

        return args

    def wrap_command(self, command):
        """
        Wrap the given command to be started with strace.

        Parameters
        ----------
        command : str, list(str) or tuple(str)
            command to be wrapped for strace

        Returns
        -------
        list(str)
            list to be passed into Popen-like calls
        """

        strace = ["strace"]

        if isinstance(command, str):
            command = [command]

        assert isinstance(command, tuple) or isinstance(command, list)

        strace.extend(self._get_args())
        strace.extend(command)
        return strace
