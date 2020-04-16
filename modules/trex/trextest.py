"""
Author(s): Dominik Tran <xtrand00@stud.fit.vutbr.cz>, Pavel Krobot <Pavel.Krobot@cesnet.cz>
Copytight: (C) 2020 CESNET
License: GPL-2.0

Base TRex test module. Provides a common frame for tests using Cisco TRex. This frame,
implemented through TRexTest class, extends parent BaseTest class:
- provides initialization of TRex handlers for control,
- handles connection to TRex servers,
- provides *some* TRex control methods. For other TRex methods use TRex API.
"""

import csv
import datetime
import fileinput
import inspect
import os
import re
import signal
import subprocess
import sys

# Appends PYTHONPATH to enable testsuite module access
sys.path.append(os.path.abspath(__file__ + "/../../../"))
from framework import BaseTest, Logger, TestResult

# Append TRex API paths
sys.path.append(os.path.join(os.path.dirname(__file__), "trex_client/v2.75/interactive"))
sys.path.append(os.path.join(os.path.dirname(__file__), "trex_client/v2.75/stf/trex_stf_lib"))
os.environ['TREX_EXT_LIBS'] = os.path.join(os.path.dirname(__file__), "trex_client/v2.75/external_libs")
from trex.stl.api import *
from trex.astf.api import *
from trex.utils.parsing_opts import decode_multiplier
from trex_client import CTRexClient

class TRexTest(BaseTest):
    """Base TRex test class extending BaseTest class.

    Tests based on this class should call _setup_trex_instance() method during _setup() phase to create TRex instances.
    See _setup_trex_instance() method's docstring for more information.

    Attributes
    ----------
    _trex_client : list(CTRexClient)
        List of objects for communication with TRex daemons.
    _trex_handler : list(Union[ASTFClient, STLClient])
        List of handlers for communication with TRex instances.
    _manual_debug : bool
        Manual debug flag. If it is set to True TRex connection related steps are skipped
        and expected to be handled manually.
    """

    def __init__(self, args, output_dir, logger=None):
        """
        Parameters
        ----------
        args : ArgumentParser.parseargs() populated namespace
            Set of parsed arguments.
        output_dir : str
            Path to the output directory where test outputs will be stored.
        logger : logging.Logger, optional
            Initialized logging facility object. If a logger is not passed, it is
            created later in the _setup() method.
        """

        super().__init__(args, output_dir, logger)

        self._manual_debug = args.manual_debug

        self._trex_client = []
        self._trex_handler = []


    def _prologue(self):
        """Perform environment preparation common for all test cases within a test.

        Extends BaseTest._prologue() method:
        Connect to TRexes and acquire physical ports (if manual debugging is turned off
        none of these steps is performed).
        """

        super()._prologue()

        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping TRex reservations and preparation.')
        else:
            for hnd in self._trex_handler:
                self._logger.info('Connecting to TRex ({}:{}) ...'.format(hnd.ctx.server, hnd.ctx.async_port))

                hnd.connect()
                self._logger.info('Acquiring all available physical ports ...')
                # Note: reset() without arguments acquires all available physical ports.
                # If you need to use only one physical port, then set TRex configuration file
                # to use one 'dummy' port, which cannot be acquired.
                hnd.reset()

                for port in hnd.get_all_ports():
                    self._logger.info('Port {} speed: {} GB.'.format(port, hnd.get_port_attr(port)['speed']))


    def _epilogue(self):
        """Clean up environment set up common for all test cases within a test.

        Extends BaseTest._epilogue() method:
        Disconnects from TRex instances. Stops TRex servers. (iff manual debugging is turned off).
        """

        super()._epilogue()

        if self._manual_debug:
            self._logger.info('Manual debugging mode is ON. Skipping disconnecting from and stopping TRexes.')
        else:
            for hnd in self._trex_handler:
                self._logger.info('Disconnecting from TRex ({}:{}) ...'.format(hnd.ctx.server, hnd.ctx.async_port))
                hnd.disconnect()
            self._trex_handler = None

            for client in self._trex_client:
                self._logger.info('Stopping TRex ({}:{}) ...'.format(client.trex_host, client.trex_daemon_port))
                client.stop_trex()
            self._trex_client = None


    # -----------------------------------------------------------------------
    # TREX METHODS
    # -----------------------------------------------------------------------

    def _setup_trex_instance(self, server, daemon_port, sync_port, async_port, config_file, statefulness):
        """Creates new TRex instance.

        This method should be called in _setup() method of test to create TRex instances. For example
        first instance for generation of legitimate traffic and second instance for generation of (D)DoS attack.

        Parameters
        ----------
        server : str
            IP address or hostname.
        daemon_port : int
            Port on which TRex daemon listens. Each daemon can manage only one TRex instance.
        sync_port : int
            TRex RPC port.
        async_port : int
            TRex ASYNC port (subscriber port).
        config_file : str
            TRex configuration file. This file must exist on TRex server. Can be set as relative or absolute path.
        statefulness : str
            TRex instance will generate stateteful ('astf', for TCP+UDP) or stateless ('stl', for UDP) traffic.

        Raises
        ------
        ValueError
            If statefulness is not set correctly.

        Returns
        -------
        Union[ASTFClient, STLClient]
            TRex handler.
        """

        if statefulness not in ('stl', 'astf'):
            raise ValueError("Bad statefulness. Expected 'stl' or 'astf', got '{}'".format(statefulness))

        handler = None
        if not self._manual_debug:
            self._start_trex_server(server, daemon_port, config_file, statefulness)
            handler = self._create_trex_handler(server, sync_port, async_port, statefulness)

        return handler


    def _start_trex_server(self, server, daemon_port, config_file, statefulness):
        """Create TRex client object and start TRex.

        Parameters
        ----------
        server : str
            IP address or hostname.
        daemon_port : int
            Port on which TRex daemon listens. Each daemon can manage only one TRex instance.
        config_file : str
            TRex configuration file. This file must exist on TRex server. Can be set as relative or absolute path.
        statefulness : str
            Stateteful ('astf', for TCP+UDP) or stateless ('stl', for UDP).
        """

        # Create TRex client object for communication with TRex daemon
        self._logger.info('Connecting to TRex daemon ({}:{}) ...'.format(server, daemon_port))
        trex_client = CTRexClient(trex_host=server, trex_daemon_port=daemon_port)

        # Start TRex instance
        self._logger.info('Starting {} TRex ...'.format(statefulness))
        if statefulness == "stl":
            trex_client.start_stateless(cfg=config_file, no_scapy_server=True)
        else:
            trex_client.start_astf(cfg=config_file)

        self._trex_client.append(trex_client)


    def _create_trex_handler(self, server, sync_port, async_port, statefulness):
        """Create TRex API handler.

        Parameters
        ----------
        server : str
            IP address or hostname.
        sync_port : int
            RPC port.
        async_port : int
            ASYNC port (subscriber port).
        statefulness : str
            Stateteful ('astf') or stateless ('stl').

        Returns
        -------
        Union[ASTFClient, STLClient]
            TRex handler.
        """

        # Create handler
        handler = None

        if statefulness == "stl":
            handler = STLClient(server = server, sync_port=sync_port, async_port=async_port)
        else:
            handler = ASTFClient(server = server, sync_port=sync_port, async_port=async_port)

        self._trex_handler.append(handler)
        return handler


    def _reset_ports(self, handler=None):
        """Clear statistics and remove all streams/profiles for given TRex instance.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. Default value is None, which means all TRex instances.
        """

        if handler is None:
            for hnd in self._trex_handler:
                hnd.reset()
        else:
            handler.reset()


    def _add_stl_stream(self, handler, stream_file, physical_ports, stream_variable="stl_stream"):
        """Add stateless stream which defines traffic/packets.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient]
            Specifies instance of TRex.
        stream_file : str
            Path to the stream file. File defines stream in Python using TRex API.
            File MUST define stream_variable variable. Variable must be STLStream()
            type or a list containing STLStream() elements.
        physical_ports : Union[list(int), int]
            Specifies to which physical port(s) stream will be added.
        stream_variable : str, optional
            Custom name of mandatory variable.

        Raises
        ------
        NameError
            If mandatory variables are not defined in stream_file.
        """

        _locals = locals()
        exec(open(stream_file).read(), globals(), _locals)

        if (stream_variable not in _locals):
            err_msg = "Stream file '{}' does not define mandatory '{}' variable!".format(stream_file, stream_variable)
            raise NameError(err_msg)

        handler.add_streams(_locals[stream_variable], ports = physical_ports)


    def _add_astf_profile(self, handler, profile_file, profile_variable="astf_profile"):
        """Add stateful profile which defines traffic/packets.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient]
            Specifies instance of TRex.
        profile_file : str
            Path to the profile file. File defines profile in Python using TRex API.
            File MUST define profile_variable variable of ASTFProfile() type.
        profile_variable : str, optional
            Custom name of mandatory ASTFProfile() variable.

        Raises
        ------
        NameError
            If mandatory variable profile_variable is not defined in profile_file.
        """

        _locals = locals()
        exec(open(profile_file).read(), globals(), _locals)

        if profile_variable not in _locals:
            err_msg = "Profile file '{}' does not define mandatory '{}' variable!".format(profile_file, profile_variable)
            raise NameError(err_msg)

        handler.load_profile(_locals[profile_variable])


    def _stl_start(self, handler=None, physical_ports=None, duration=-1, target_speed="1", **kwargs):
        """Start generating packets defined earlier by method _add_stl_stream().

        Parameters
        ----------
        handler : STLClient
            Specifies instance of TRex. If not set, use all available stateless TRex instances.
        physical_ports : Union[list(int), int]
            Specifies which port(s) will be used to generate packets. If not set,
            use all ports where stream(s) were defined (by _add_stl_stream() method). Note that
            if you use handler default value, then you have to leave this parameter on default value too.
        duration : int, optional
            Specifies duration of generation in seconds. Default value is -1, which means
            generating until explicit _stop() method is called.
        target_speed : str, optional
            Desired attack speed. Can be set in bps or pps with k/m/g prefixes. Examples:
            "10kpps", "100mbps", "20.6gbps". Default value is "1", meaning default speed defined
            in stream/profile file.
        """

        if handler is not None and physical_ports is not None:
            handler.start(ports = physical_ports, duration = duration, mult=target_speed, **kwargs)
        else:
            if handler is not None and physical_ports is None:
                for pid in handler.get_acquired_ports():
                    if handler.ports[pid].streams:
                        handler.start(ports = pid, duration = duration, mult=target_speed, **kwargs)
            else:
                for hnd in self._trex_handler:
                    if isinstance(hnd, STLClient):
                        for pid in hnd.get_acquired_ports():
                            if hnd.ports[pid].streams:
                                hnd.start(ports = pid, duration = duration, mult=target_speed, **kwargs)


    def _astf_start(self, handler, duration=-1, mult=1):
        """Start generating traffic defined earlier by method _add_astf_profile().

        Parameters
        ----------
        handler : ASTFClient
            Specifies instance of TRex. If not set, use all available stateful TRex instances.
        duration : int, optional
            Specifies duration of generation in seconds. Default value is -1, which means
            generating until explicit _stop() method is called.
        mult : int, optional
            Multiply total CPS (Connections per second) of profile by this value.
        """

        if handler is not None:
            handler.start(duration = duration, mult=mult)
        else:
            for hnd in self._trex_handler:
                if isinstance(hnd, ASTFClient):
                    hnd.start(duration = duration, mult=mult)


    def _stop(self, handler = None):
        """Stop generating traffic and/or attack.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. Default value is None, which
            means all TRex instances.
        """

        if handler is None:
            for hnd in self._trex_handler:
                hnd.stop()
        else:
            handler.stop()


    def _wait(self, handler=None):
        """Wait until packet generation is over.

        This method will block until generation is over. Do NOT use if
        duration of generation is set as "-1" (default value), otherwise
        method will block forever.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. Default value is None, which
            means all TRex instances (whichever finishes later).
        """

        if handler is None:
            for hnd in self._trex_handler:
                hnd.wait_on_traffic()
        else:
            handler.wait_on_traffic()


    def _get_stats(self, handler):
        """Return statistics for given TRex instance.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient]
            Specifies instance of TRex.

        Raises
        ------
        ValueError
            If instance is set incorrectly.

        Returns
        -------
        dict
            Statistics in form of a dictionary (key:value)
        """

        if isinstance(handler, STLClient):
            return handler.get_stats()

        if isinstance(handler, ASTFClient):
            return handler.get_stats(skip_zero=False)


    def _u2i(self, unit):
        """Convert bandwidth units like "10mbps", "94kpps", "10.67gbps" to integer.

        Parameters
        ----------
        unit : str
            String to be converted into integer.

        Returns
        -------
        int
            Converted value.
        """

        return int(decode_multiplier(unit)['value'])
