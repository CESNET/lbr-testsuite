"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>, (+ Matus Burzala)
Copytight: (C) 202O CESNET
License: GPL-2.0

This module contains Logger class for testing suite.

Logger class is a wrapper over python logging facility. Information about test
execution and results is logged to stdout and to a log file. This log file is
stored inside a selected output directory and is named based on a class name
of the class creating a logger and date a time of a tests execution.
"""

import datetime
import fileinput
import logging
import os


class Logger:
    """Logger class for logging test progress.

    Attributes
    ----------
    _class_name : str
        Name of a calling class used for identification.
    _output_dir : str
        Path to the output directory where log will be stored.

    Methods
    -------
    create_logger()
        Creates output directory if it does not exists and initializes logging facility
        for stdout and log file.
    """

    def __init__(self, class_name, output_dir):
        """
        Parameters
        ----------
        class_name : str
            Name of a calling class.
        output_dir : str
            Path to the output directory where logs will be stored.
        """

        self._class_name = class_name
        self._output_dir = output_dir


    def create_logger(self):
        """Set up logging.

        Method creates output directory if it does not exists, sets logging verbosity to INFO
        and initializes logging facility for logging to log file and stdout.

        Returns
        -------
        logging.Logger
            Initialized logging facility object.
        """

        self._create_dir(self._output_dir)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        file_name = self._get_file_name()
        log_file = os.path.join(self._output_dir, file_name)

        file_handler = logging.FileHandler(log_file)
        stream_handler = logging.StreamHandler()

        formatter = logging.Formatter('%(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        return logger


    def _get_file_name(self):
        """Generate log file name.

        Log file name is created from test class name and current date and time.

        Returns
        -------
        str
            Log file name.
        """

        date_time = self._get_file_name_date()
        filename = self._class_name.lower() + '_' + date_time + '.log'
        return filename


    @staticmethod
    def _get_file_name_date():
        """Create date and time component of log filename.

        Returns
        -------
        str
            Date and time component of log file name.
        """

        return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


    @staticmethod
    def _create_dir(name):
        """Create a directory wit specified name.

        Parameters
        ----------
        name : str
            Path to the directoy to create
        """

        if not os.path.exists(name):
            os.mkdir(name)
