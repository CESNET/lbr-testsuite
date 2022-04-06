"""
    Author(s): Jan Kucera <jan.kucera@cesnet.cz>, Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2019 CESNET

    Description: Provides a class simulating standard StcPython but sending all
    commands over the network.
"""

import logging
import pickle
import socket
import struct


class StcPythonTCP:
    """Class simulating standard StcPython, sending all commands over
    the network.
    """

    def __init__(self, host, port):
        self._socket = socket.create_connection((host, port))
        self._logger = logging.getLogger("STC")

    def _recv_msg(self):
        self._logger.debug("Receiving message...")
        buffer = bytearray()
        while len(buffer) < 4:
            buffer.extend(self._socket.recv(1500))

        (msg_len,) = struct.unpack("<I", buffer[:4])
        del buffer[:4]
        while len(buffer) < msg_len:
            buffer.extend(self._socket.recv(1500))

        self._logger.debug("Received message - {}B".format(len(buffer)))
        return pickle.loads(buffer)

    def _send_msg(self, msg):
        self._logger.debug("Sending message: {}".format(msg))
        raw_data = pickle.dumps(msg)
        data = struct.pack("<I", len(raw_data)) + raw_data
        sent = self._socket.send(data)
        self._logger.debug("Sent message - {}B".format(sent))

    def _process_command(self, command, args, kwargs):
        self._send_msg({"function": command, "args": args, "kwargs": kwargs})
        response = self._recv_msg()

        if isinstance(response, Exception):
            raise response
        else:
            return response

    def __getattr__(self, item):
        if not item in {
            "apply",
            "config",
            "connect",
            "create",
            "delete",
            "disconnect",
            "get",
            "help",
            "log",
            "perform",
            "release",
            "reserve",
            "sleep",
            "subscribe",
            "unsubscribe",
            "waitUntilComplete",
        }:
            return self.__getattribute__(item)

        def call_wrapper(*args, **kwargs):
            return self._process_command(item, args, kwargs)

        return call_wrapper
