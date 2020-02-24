"""
    Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz> (+ Matus Burzala)
    Copyright: (C) 2019 CESNET
    Licence: GPL-2.0

    Description: Logger class for testing suite

    This is a wrapper on python logging facility. It creates directory and logfile for logging and
    initializes logger object.
"""

import datetime
import fileinput
import logging
import os


class Logger:

    def __init__(self, class_name, output_dir):
        self._class_name = class_name
        self._output_dir = output_dir


    def _get_file_name(self):
        """
        Generate file prefix based on test class file name and currect date-time
        """
        date_time = self._get_file_name_date()
        prefix = self._class_name.lower() + '_' + date_time + '.log'

        return prefix


    def create_logger(self):
        """
        Setup logger to log to the log file and standard output
        :return: Initialized logging.getLogger() object.
        """
        self.create_dir(self._output_dir)

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


    @staticmethod
    def _get_file_name_date():
        """
        Return date component of file name.
        """
        return datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


    @staticmethod
    def create_dir(name):
        """
        Creates directory wit specified name.
        """
        if not os.path.exists(name):
            os.mkdir(name)
