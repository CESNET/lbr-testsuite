"""
Copyright: (C) 2023 CESNET, z.s.p.o.

Spirent server connector.
"""

# Run this script only with the Python packed with the Spirent Test Center

# Prepare PATHs to Spirent Python API
import os
import sys


os.environ["STC_PRIVATE_INSTALL_DIR"] = (
    "C:\\Program Files\\Spirent Communications\\Spirent TestCenter 5.32\\Spirent TestCenter Application"
)
sys.path.append(
    "C:\\Program Files\\Spirent Communications\\Spirent TestCenter 5.32\\Spirent TestCenter Application\\API\\Python"
)

import argparse  # noqa E402
import inspect  # noqa E402
import logging  # noqa E402
import multiprocessing as mp  # noqa E402
import pickle  # noqa E402
import socket  # noqa E402
import socketserver  # noqa E402
import struct  # noqa E402


_this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(_this_dir))
from stcapi.StcPythonTcl import StcPythonTcl  # noqa E402


# Global variable used for thread synchronization
SERVER_STOP = False


class ServerStopException(Exception):
    """Exception raised when is requested to stop the TCP server"""

    pass


class STCManager:
    """Wrapper around StcPython allowing calls its methods through names"""

    def __init__(self, logger):
        self._stc = StcPythonTcl()
        self._logger = logger.getChild("STC")
        self._logger.debug("Loaded")

    def __call__(self, method_name, *args, **kwargs):
        if hasattr(self._stc, method_name):
            method = getattr(self._stc, method_name)
        else:
            raise AttributeError(
                "Method '{}' is not part of the STC API.".format(method_name)
            ) from None

        if inspect.ismethod(method):
            self._logger.debug("Calling method {}".format(method_name))
            return method(*args, **kwargs)
        else:
            raise AttributeError(
                "Given method '{}' is not valid method for the STC API.".format(method_name)
            ) from None


def stc_process(pipe, logger_name):
    """
    The implementation of main function for newly spawned process. It performs commands received through the pipe and
    send back their results.
    """

    logger = logging.getLogger(logger_name).getChild("Process")
    try:
        logging.basicConfig(level=logging.DEBUG)
        logger.debug("Started")
        stc = STCManager(logger)

        try:
            while True:
                msg = pipe.recv()
                if isinstance(msg, str) and msg == "exit":
                    break
                try:
                    result = stc(msg["function"], *msg["args"], **msg["kwargs"])
                except Exception as e:
                    pipe.send(e)
                else:
                    pipe.send(result)
        except Exception as e:
            logger.debug("Unexpectedly terminated", exc_info=e)
        else:
            logger.debug("Stopped.")
    except KeyboardInterrupt:
        logger.debug("Interrupted.")


class ConnectionHandler(socketserver.BaseRequestHandler):
    """Handler for every new connection."""

    # noinspection PyAttributeOutsideInit
    def setup(self):
        """
        Start process which performs all STC commands for given connection. It also initialize logger and activates
        timeout for the socket.
        """
        self._logger = logging.getLogger("Client").getChild("{}".format(self.client_address[1]))
        self._logger.info("New connection: IP: {}, Port: {}".format(*self.client_address))
        self._pipe, proc_pipe = mp.Pipe()
        self._process = mp.Process(target=stc_process, args=(proc_pipe, self._logger.name))
        self._process.start()
        self.request.settimeout(1)

    def handle(self):
        """Receive STC message over the network and forward it to the process which performs it."""
        try:
            while True:
                # Receive new STC command
                msg = self._recv_msg()

                if type(msg) is not dict:
                    raise TypeError("Received invalid message.")

                self._logger.debug("Received msg: {}".format(msg))

                if "args" not in msg:
                    msg["args"] = []

                if "kwargs" not in msg:
                    msg["kwargs"] = {}

                # Send command and forward its result over the network.
                self._pipe.send(msg)
                self._send_msg(self._pipe.recv())
        except (ServerStopException, OSError):
            pass
        except Exception as e:
            self._logger.exception(e)
            raise

    def finish(self):
        """Send exit command to worker and wait until it ends."""
        self._logger.info("Connection closed.")
        self._pipe.send("exit")
        self._process.join()

    def _recv(self, length):
        """Receive data over the network. Also checks for stop request from the main thread."""
        while not SERVER_STOP:
            try:
                data = self.request.recv(length)
                if len(data) == 0:
                    raise OSError("Connection closed")
                return data
            except socket.timeout:
                pass
        raise ServerStopException()

    def _recv_msg(self):
        """Receive valid STC command and returns it."""
        self._logger.debug("Waiting for message...")
        buffer = bytearray()
        while len(buffer) < 4:
            buffer.extend(self._recv(1500))

        (msg_len,) = struct.unpack("<I", buffer[:4])
        del buffer[:4]
        while len(buffer) < msg_len:
            buffer.extend(self._recv(1500))

        self._logger.debug("Received message - {}B".format(4 + len(buffer)))
        return pickle.loads(buffer)

    def _send_msg(self, msg):
        """Format and send msg over the network."""
        raw_data = pickle.dumps(msg)
        data = struct.pack("<I", len(raw_data)) + raw_data
        sent = self.request.send(data)
        self._logger.debug("Sent message - {}B".format(sent))


class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Define TCP server whci creates thread for every incoming connection."""

    allow_reuse_address = True


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--listen", help="IP address for listening.", default="")
    parser.add_argument(
        "-p", "--port", help="Port number for incoming connections.", type=int, default=42000
    )
    args = parser.parse_args()

    logging.getLogger().info("Starting server")
    server = ThreadingTCPServer((args.listen, args.port), ConnectionHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        SERVER_STOP = True
        server.shutdown()
