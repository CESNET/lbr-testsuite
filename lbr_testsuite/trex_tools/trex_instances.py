"""
Author(s): Dominik Tran <tran@cesnet.cz>, Pavel Krobot <Pavel.Krobot@cesnet.cz>
Copyright: (C) 2021 CESNET

Base TRex test module. Provides a common frame for tests using Cisco TRex.
 | TRex_Instances class contains following features:
 | - provides initialization of TRex handlers for control,
 | - handles connection to TRex servers,
 | - provides *some* TRex control methods. For other TRex methods use
 | standard TRex API, see
 | `Python Automation API <https://trex-tgn.cisco.com/trex/doc/>`_.
"""

from functools import partial

import logging
global_logger = logging.getLogger(__name__)

import lbr_trex_client.paths  # noqa: F401

from trex.stl.api import *
from trex.astf.api import *
from trex.utils.parsing_opts import decode_multiplier
from trex_client import CTRexClient
from trex_exceptions import TRexInUseError


class TRex_Instances():
    """Base TRex class.

    Tests should call :meth:`~trex_tools.trex_instances.TRex_Instances.setup_trex_instance`
    during setup phase to create single TRex instance.
    See :meth:`~trex_tools.trex_instances.TRex_Instances.setup_trex_instance`
    for more information.

    Attributes
    ----------
    _trex_daemon_handlers : CTRexClient
        List of all daemon handlers created by :meth:`~trex_tools.trex_instances.TRex_Instances.setup_trex_instance`
        for communication with TRex daemon.
    _trex_handlers : list(Union[ASTFClient, STLClient])
        List of all handlers created by :meth:`~trex_tools.trex_instances.TRex_Instances.setup_trex_instance`
        for communication with TRex instances.
    """

    def __init__(self):

        self._trex_daemon_handlers = []
        self._trex_handlers = []

    # -----------------------------------------------------------------------
    # TREX METHODS
    # -----------------------------------------------------------------------

    def setup_trex_instance(
        self,
        server,
        daemon_port,
        sync_port,
        async_port,
        config_file,
        statefulness,
        force_use=False,
        pyt_request=None,
        **trex_cmd_options
    ):
        """Create, start and connect to a new TRex instance.

        This method should be called during setup phase of test to
        create and connect to a single TRex instance. Method can be
        called repeatedly with different arguments to create various
        TRex instances. For example it can be used to create first
        instance for generation of legitimate stateful (TCP/HTTP)
        traffic and then second instance for generation of
        stateless (UDP/TCP SYN flood...) DDoS attack. Note that
        TRex can be started in either stateful or stateless mode.
        So if you need to generate both traffic types, you
        will need to setup two instances.

        Every TRex instance (its handler) created by this method is
        stored in *instance* of ``TRex_Instances`` class.

        Method first connects to TRex daemon and commands him to start
        TRex instance. Once TRex instance is started, method connects
        to it and then established connection handler is returned to
        the user. Most methods of this ``TRex_Instances`` class need
        this handler as an input argument. Depending on *statefulness*
        parameter returned type is either
        `STLClient <https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/client_code.html#stlclient-class>`_ or
        `ASTFClient <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/client_code.html#astfclient-class>`_.

        Here's an example of simple use case flow with one TRex instance::

            TEST                      DAEMON                     TREX
            setup_trex_instance(statefulness='stl')
            Connect------------------------>
            <-----------------------------OK
            Start TRex--------------------->
                                      Start------------------------->
                                                                START
                                      <----------------------------OK
            <-----------------------------OK
            Connect------------------------------------------------->
            <------------------------------------------------------OK

            add_streams()
            Add stateless stream of packets------------------------->
            <------------------------------------------------------OK

            stl_start(duration=N)
            Start generating packets for N seconds ----------------->
            <------------------------------------------------------OK


            finalizer (if using pytest) or disconnect()
            Disconnect---------------------------------------------->
            <------------------------------------------------------OK
            Terminate TRex---------------------->
                                      Terminate--------------------->
                                      <----------------------------OK
                                                                 STOP
            <-----------------------------OK

        Parameters
        ----------
        server : str
            IP address or hostname of TRex machine.
        daemon_port : int
            Port on which TRex daemon listens.
            Each daemon can manage only one TRex instance.
        sync_port : int
            TRex RPC port.
        async_port : int
            TRex ASYNC port (subscriber port). It's usually
            *sync_port*-1.
        config_file : str
            TRex configuration file. This file must exist on TRex
            machine. Can be set as relative or absolute path.
        statefulness : str
            TRex will generate either stateful
            (``astf``, TCP + possibly UDP) or stateless
            (``stl``, supports Scapy+Field Engine) traffic.
        force_use : bool
            Kill running TRex instance before start.
            Set to True if you get ``TRexInUseError`` error.
        pyt_request : FixtureRequest, optional
            Special **pytest** fixture, here used for adding of a
            finalizer. Parameter is **optional** and this method can
            be used even without pytest framework. In that case, you
            will also need to call
            :meth:`~trex_tools.trex_instances.TRex_Instances.disconnect`
            manually.
        trex_cmd_options : dict, optional
            This is an advanced option used for `start_stateles()
            <https://trex-tgn.cisco.com/trex/doc/cp_docs/api/client_code.html#trex_client.CTRexClient.start_stateless>`_.
            Use only in specific cases.

        Raises
        ------
        ValueError
            If statefulness is not set correctly.
        TRexInUseError
            If TRex is already taken. Set force_use to True to overcome
            this. Such situation can happen if there is some error
            (or interrupt like Ctrl+C) during initialization before
            finalizer function (in case of pytest) is registered.
            Otherwise some other user might be using TRex at the same
            time.

        Returns
        -------
        Union[ASTFClient, STLClient]
            TRex handler.
        """

        if statefulness not in ('stl', 'astf'):
            raise ValueError(f'Bad statefulness. Expected "stl" or "astf", got "{statefulness}"')

        trex_daemon_handler = None
        trex_handler = None

        # Connect to and create handler for communication with TRex daemon
        # CTRexClient() class doesn't have any explicit disconnect() method -> no finalizer
        global_logger.debug(f'Connecting to TRex daemon ({server}:{daemon_port}) ...')
        trex_daemon_handler = CTRexClient(trex_host=server, trex_daemon_port=daemon_port)

        if force_use:
            trex_daemon_handler.force_kill(confirm=False)

        # Command TRex daemon to start TRex instance
        global_logger.debug(f'Starting {statefulness} TRex ...')
        try:
            if statefulness == "stl":
                trex_daemon_handler.start_stateless(cfg=config_file, **trex_cmd_options)
                self._trex_daemon_handlers.append(trex_daemon_handler)
            else:
                trex_daemon_handler.start_astf(cfg=config_file, **trex_cmd_options)
                self._trex_daemon_handlers.append(trex_daemon_handler)

        except TRexInUseError as e:
            global_logger.error('TRex is already running. Call this method with force_use=True to kill TRex.')
            # It is recommended to catch this exception and raise additional message to inform user
            # about solutions based on your testing framework. Eg. launching test again with command
            # line parameter like --trex-force-use that will ensure calling this method with force_use=True.
            raise e

        if statefulness == "stl":
            trex_handler = STLClient(server=server, sync_port=sync_port, async_port=async_port)
        else:
            trex_handler = ASTFClient(server=server, sync_port=sync_port, async_port=async_port)

        global_logger.debug(f'Connecting to TRex ({trex_handler.ctx.server}:' +
                            f'[{trex_handler.ctx.async_port},{trex_handler.ctx.sync_port}]) ...')
        trex_handler.connect()
        self._trex_handlers.append(trex_handler)
        global_logger.debug('Acquiring all available physical ports ...')

        # Note: reset() without arguments acquires all available physical ports.
        # If you need to use only one physical port, then set TRex configuration file
        # to use one 'dummy' port, which cannot be acquired.
        trex_handler.reset()
        for port in trex_handler.get_all_ports():
            global_logger.debug(f'Port {port} speed: {trex_handler.get_port_attr(port)["speed"]} GB.')

        # Can be used only in pytest framework, otherwise see disconnect() method
        def finalizer(self, trex_handler):

            self.disconnect(trex_handler)

        if pyt_request:
            pyt_request.addfinalizer(partial(finalizer, self, trex_handler))

        return trex_handler

    def disconnect(self, handler):
        """Disconnect from TRex instance and terminate it via it's daemon.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex.
        """

        global_logger.debug(f'Disconnecting from TRex ({handler.ctx.server}:' +
                            f'[{handler.ctx.async_port},{handler.ctx.sync_port}]) ...')
        handler.disconnect()

        # Daemon handler has same index in _TDH array as TRex handler has in _TH array, so it can be used to find it
        trex_daemon_handler = self._trex_daemon_handlers[self._trex_handlers.index(handler)]

        global_logger.debug(f'Terminating TRex (via its daemon {trex_daemon_handler.trex_host}:' +
                            f'{trex_daemon_handler.trex_daemon_port}) ...')
        trex_daemon_handler.stop_trex()

        self._trex_handlers.remove(handler)
        self._trex_daemon_handlers.remove(trex_daemon_handler)

    def reset_ports(self, handler=None):
        """Stop the traffic, remove all streams, clear stats and
        (re)acquire ports for given TRex instance.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. None (default) means all
            TRex instances known to (this instance of) class.
        """

        if handler:
            handler.reset()
        else:
            for hnd in self._trex_handlers:
                hnd.reset()

    def stl_start(self, handler=None, physical_ports=None, duration=-1, mult='1', **kwargs):
        """Start generating packets from stateless TRex.

        Given ports must be configured with
        `STLStream(s) <https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/profile_code.html#stlprofile-class>`_
        so that they know what to generate. See
        :class:`~trex_tools.trex_stl_stream_generator.TRex_Stl_Stream_Generator`
        for example of some STLStream(s).

        Parameters
        ----------
        handler : STLClient
            Specifies instance of TRex. If not set, use all available
            stateless TRex instances known to (this instance of) class.
        physical_ports : Union[list(int), int]
            Specifies which port(s) will be used to generate packets.
            If not set, use all ports where stream(s) were defined.
        duration : float, optional
            Specifies duration of generation in seconds. Default value
            is -1, which means generating until explicit
            :meth:`~trex_tools.trex_instances.TRex_Instances.stop`
            is called.
        mult : str, optional
            Set speed/volume of generation. Can be set in bps/pps
            with optional k/m/g prefixes, percents of port bandwidth or
            just a number (multiplier of default speed defined by stream).
            Examples: ``"2", "10kpps", "300mbps", "100%", 20.666gbps"``.
            Default value is "1", meaning default speed defined by stream.
        kwargs: dict, optional
            Additional arguments passed to official `start()
            <https://trex-tgn.cisco.com/trex/doc/cp_stl_docs/api/client_code.html#trex.stl.trex_stl_client.STLClient.start>`_
            method.
        """

        params = kwargs
        params['duration'] = duration
        params['mult'] = mult

        # Get list of physical port IDs that are configured with streams
        def stl_pid(hnd):
            return (pid for pid in hnd.get_acquired_ports() if hnd.ports[pid].streams)

        if handler:
            if physical_ports:
                handler.start(ports=physical_ports, **params)
            else:
                for pid in stl_pid(handler):
                    handler.start(ports=pid, **params)
        else:
            # Get list of stl handlers
            stl_hnd = (h for h in self._trex_handlers if isinstance(h, STLClient))

            if physical_ports:
                for hnd in stl_hnd:
                    hnd.start(ports=physical_ports, **params)
            else:
                for hnd in stl_hnd:
                    for pid in stl_pid(hnd):
                        hnd.start(ports=pid, **params)

    def astf_start(self, handler=None, duration=-1, mult=1, **kwargs):
        """Start generating packets from stateful TRex.

        Given TRex instance must be configured with
        `ASTFProfile <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprofile-class>`_
        so thatit knows what to generate. See
        :class:`~trex_tools.trex_astf_profile_generator.TRex_Astf_Profile_Generator`
        for example of some ASTFProfiles.

        Parameters
        ----------
        handler : STLClient
            Specifies instance of TRex. If not set, use all available
            stateful TRex instances known to (this instance of) class.
        duration : float, optional
            Specifies duration of generation in seconds. Default value
            is -1, which meansgenerating until explicit
            :meth:`~trex_tools.trex_instances.TRex_Instances.stop`
            is called.
        mult : int, optional
            Multiply total CPS (Connections per second) of ASTFProfile
            by this value.
        kwargs: dict, optional
            Additional arguments passed to official `start()
            <https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/client_code.html#trex.astf.trex_astf_client.ASTFClient.start>`_
            method.
        """

        params = kwargs
        params['duration'] = duration
        params['mult'] = mult

        if handler:
            handler.start(**params)
        else:
            astf_hnd = (h for h in self._trex_handlers if isinstance(h, ASTFClient))
            for hnd in astf_hnd:
                hnd.start(**params)

    def stop(self, handler=None):
        """Stop generating traffic.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. None (default) means all
            TRex instances known to (this instance of) class.
        """

        if handler:
            handler.stop()
        else:
            for hnd in self._trex_handlers:
                hnd.stop()

    def wait(self, handler=None, timeout=None):
        """Wait until packet generation finished.

        This method will block until generation is over
        or until *timeout* is reached.

        Parameters
        ----------
        handler : Union[ASTFClient, STLClient], optional
            Specifies instance of TRex. None (default) means all
            TRex instances (whichever finishes later) known to
            (this instance of) class.
        timeout : int, optional
            Timeout in seconds. None (default) means
            no timeout. In that case method can block forever
            if duration of generation is left at default value (-1).
        """

        if handler:
            handler.wait_on_traffic(timeout=timeout)
        else:
            for hnd in self._trex_handlers:
                hnd.wait_on_traffic(timeout=timeout)

    def get_stats(self, handler):
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
            Statistics in form of a dictionary (key:value). Items in
            dict will vary based on configuration and statefulness of
            TRex.
        """

        if isinstance(handler, STLClient):
            return handler.get_stats()
        elif isinstance(handler, ASTFClient):
            return handler.get_stats(skip_zero=False)
        else:
            raise ValueError(f'Bad handler. Expected STLClient or ASTFClient type, got "{type(handler)}"')

    @staticmethod
    def u2i(unit):
        """Convert bandwidth units like
        ``"10mbps", "94kpps", "10.67gbps"`` to integer.

        Parameters
        ----------
        unit : str
            String to be converted into integer.
            String *cannot* contain spaces (like "10 mpps").
            String *can* contain capital letters (like "10Mpps").

        Returns
        -------
        int
            Converted value.
        """

        return int(decode_multiplier(unit.lower())['value'])

    @staticmethod
    def bps_L2_to_L3(bps_l2, fixed_packet_size, vlan=True):
        """Convert L2 bits per second value to L3 bits per second value.

        TRex's bits per second (bps) units are computed on L2 layer.
        Some devices work with L3 bps values,
        meaning that whole L2 header (6B dstMAC, 6B srcMAC,
        2B EthType, 4B CRC [,+4B VLAN]) of each packet is not counted.
        To properly convert L2 bps to L3 bps, every generated packet
        must be of fixed size. If your packet size changes during
        generation, then this method won't work correctly.

        Parameters
        ----------
        bps_l2 : Union[str, int]
            Value to be converted. Can be set as integer or
            string (then it will be converted to integer by
            :meth:`~trex_tools.trex_instances.TRex_Instances.u2i`).
        fixed_packet_size : int
            Size of packet. All generated packets must be of this size.
        vlan : bool, optional
            Determine if VLAN is used.

        Raises
        ------
        ValueError
            If passed bps_l2 argument is of "pps" type instead of "bps".

        Returns
        -------
        int
            Converted value.
        """

        if isinstance(bps_l2, str):
            if bps_l2[-3:].lower() == "pps":
                raise ValueError('Expected "bps" (bits per second) unit, but got "pps" (packets per second) unit.')
            bps_l2 = TRex_Instances.u2i(bps_l2)

        L2_header_size = 18
        if vlan:
            L2_header_size += 4

        # This ratio will always be above 1.0 because you need to
        # generate more bps on L2 to reach same value on L3
        l2_to_l3_ratio = (fixed_packet_size + L2_header_size) / fixed_packet_size

        return int(l2_to_l3_ratio * bps_l2)
