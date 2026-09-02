"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023-2026 CESNET, z.s.p.o.

Module implements TRex manager class.

Manager provides TRex generator upon request.
"""

import logging

from .trex_base import TRexZMQPortsUsedError
from .trex_configuration_file import randomize_ports, setup_cfg_file
from .trex_emulation import TRexEmulation
from .trex_legacy_stateful import TRexLegacyStateful
from .trex_stateful import TRexAdvancedStateful
from .trex_stateless import TRexStateless


global_logger = logging.getLogger(__name__)


class TRexManager:
    """TRex Manager class.

    Class manages TRex generators and provides
    methods for requesting TRex generator.

    Attributes
    ----------
    STARTUP_ATTEMPTS : int
        Number of attempts to start TRex.
        In case TRex fails to start because ZMQ (communication)
        ports are already used by another process.
        Use another ports and try again.

    Parameters
    ----------
    machine_pool : TRexMachinesPool
        Pool of available TRex machines.
    """

    STARTUP_ATTEMPTS = 5

    def __init__(self, machine_pool):
        self._pool = machine_pool

    def request_stateless(
        self,
        request,
        interface_count=1,
        core_count=6,
        specific_cores=[],
        memory_mb=None,
        memory_concurrent_flows=None,
    ):
        """Request stateless TRex generator.

        Parameters
        ----------
        request : fixture
            Special pytest fixture.
        interface_count : int, optional
            Number of physical ports/interfaces of NIC to use.
            Port ID always begins from 0.
            For example, if ``interface_count`` is 3, then
            ports ID 0, 1, 2 will be available.
        core_count : int, optional
            Count of CPU cores to use (minimum is 3).
            More cores will generally increase performance.

            Depending on number of cores, TRex might generate
            more packets/bits than expected. User will have to
            experiment with this to find optimal count.
            Some tolerance (e.g. 1 packet) could be useful
            in such situation.

            This parameter is ignored if "specific_cores" is provided.
        specific_cores : list, optional
            Ignore "core_count" and instead use cores specified
            in this list.
        memory_mb: int | None, optional
            Amount of hugepage memory (in MB) for TRex to use. Increase if TRex fails with
            "ERROR there is not enough huge-pages memory in your system" error.
            TRex generator with 3+ interfaces will split memory evenly between each interface pair.
            Note that if you set memory_mb to be more than amount of hugepages in system, then
            error message will be different and will look like this:
            "EAL: Not enough memory available on socket 0! Requested: 10000MB, available: 4096MB"
        memory_concurrent_flows : int | None, optional
            Number of TRex flow objects allocated.
            Some configurations require higher number of preallocated flow objects.
            For example: when stateful server is overwhelmed with new connection requests,
            it needs to keep more objects in memory in order to not drop active
            or new connections.
            If set too high and system has enough hugepages, TRex will fail with following error:
                "ERROR something went wrong here, more than 20M flows per core does not make sense"
            For details see parameter "dp_flows" on link
            https://trex-tgn.cisco.com/trex/doc/trex_manual.html#_memory_section_configuration

        Returns
        -------
        TRexStateless
            TRexStateless if request was successful.
        """

        return self._request_generator(
            request,
            interface_count,
            core_count,
            specific_cores,
            TRexStateless,
            memory_mb=memory_mb,
            memory_concurrent_flows=memory_concurrent_flows,
        )

    def request_stateful(
        self,
        request,
        role,
        core_count=6,
        specific_cores=[],
        memory_mb=None,
        memory_concurrent_flows=None,
    ):
        """Request advanced stateful TRex generator.

        Parameters
        ----------
        request : fixture
            Special pytest fixture.
        role: str
            TRex will act as a ``client`` or ``server``.
        core_count : int, optional
            Count of CPU cores to use (minimum is 3).
            More cores will generally increase performance.
            This parameter is ignored if "specific_cores" is provided.
        specific_cores : list, optional
            Ignore "core_count" and instead use cores specified
            in this list.
        memory_mb: int | None, optional
            Amount of hugepage memory (in MB) for TRex to use. Increase if TRex fails with
            "ERROR there is not enough huge-pages memory in your system" error.
            TRex generator with 3+ interfaces will split memory evenly between each interface pair.
            Note that if you set memory_mb to be more than amount of hugepages in system, then
            error message will be different and will look like this:
            "EAL: Not enough memory available on socket 0! Requested: 10000MB, available: 4096MB"
        memory_concurrent_flows : int | None, optional
            Number of TRex flow objects allocated.
            Some configurations require higher number of preallocated flow objects.
            For example: when stateful server is overwhelmed with new connection requests,
            it needs to keep more objects in memory in order to not drop active
            or new connections.
            If set too high and system has enough hugepages, TRex will fail with following error:
                "ERROR something went wrong here, more than 20M flows per core does not make sense"
            For details see parameter "dp_flows" on link
            https://trex-tgn.cisco.com/trex/doc/trex_manual.html#_memory_section_configuration

        Returns
        -------
        TRexAdvancedStateful
            TRexAdvancedStateful if request was successful.
        """

        assert role in ("client", "server"), f"Unknown role {role}."

        return self._request_generator(
            request,
            1,
            core_count,
            specific_cores,
            TRexAdvancedStateful,
            role,
            memory_mb,
            memory_concurrent_flows,
        )

    def request_legacy_stateful(
        self,
        request,
        interface_count=1,
        core_count=6,
        specific_cores=[],
    ):
        """Request legacy stateful TRex generator.

        Note: Legacy stateful TRex does not provide interactive API.
        Traffic is generated by starting a TRex run with a traffic
        profile file via the official handler (see TRexLegacyStateful).

        Parameters
        ----------
        request : fixture
            Special pytest fixture.
        interface_count : int
            Number of physical ports/interfaces of NIC to use.
            Port ID always begins from 0.
            For example, if ``interface_count`` is 3, then
            ports ID 0, 1, 2 will be available.
        core_count : int, optional
            Count of CPU cores to use (minimum is 3).
            More cores will generally increase performance.
            This parameter is ignored if "specific_cores" is provided.
        specific_cores : list, optional
            Ignore "core_count" and instead use cores specified
            in this list.

        Returns
        -------
        TRexLegacyStateful
            TRexLegacyStateful if request was successful.
        """

        return self._request_generator(
            request,
            interface_count,
            core_count,
            specific_cores,
            TRexLegacyStateful,
        )

    def request_emulation(
        self,
        request,
        interface_count=1,
        core_count=3,
        memory_mb=None,
        memory_concurrent_flows=None,
    ):
        """Request emulation TRex generator.

        Note: Emulation TRex runs with --software flag, which
        limits it's performance.

        Warning: Currently only one active instance of emulation
        TRex generator is supported.

        Parameters
        ----------
        request : fixture
            Special pytest fixture.
        interface_count : int, optional
            Number of physical ports/interfaces of NIC to use.
            Port ID always begins from 0.
            For example, if ``interface_count`` is 3, then
            ports ID 0, 1, 2 will be available.
        core_count : int, optional
            Count of CPU cores to use (minimum is 3).
            More cores will generally increase performance.
        memory_mb: int | None, optional
            Amount of hugepage memory (in MB) for TRex to use. Increase if TRex fails with
            "ERROR there is not enough huge-pages memory in your system" error.
            TRex generator with 3+ interfaces will split memory evenly between each interface pair.
            Note that if you set memory_mb to be more than amount of hugepages in system, then
            error message will be different and will look like this:
            "EAL: Not enough memory available on socket 0! Requested: 10000MB, available: 4096MB"
        memory_concurrent_flows : int | None, optional
            Number of TRex flow objects allocated.
            Some configurations require higher number of preallocated flow objects.
            For example: when stateful server is overwhelmed with new connection requests,
            it needs to keep more objects in memory in order to not drop active
            or new connections.
            If set too high and system has enough hugepages, TRex will fail with following error:
                "ERROR something went wrong here, more than 20M flows per core does not make sense"
            For details see parameter "dp_flows" on link
            https://trex-tgn.cisco.com/trex/doc/trex_manual.html#_memory_section_configuration

        Returns
        -------
        TRexEmulation
            TRexEmulation if request was successful.
        """

        return self._request_generator(
            request,
            interface_count,
            core_count,
            [],
            TRexEmulation,
            memory_mb=memory_mb,
            memory_concurrent_flows=memory_concurrent_flows,
        )

    def _request_generator(
        self,
        request,
        interface_count,
        core_count,
        specific_cores,
        trex_class,
        role=None,
        memory_mb=None,
        memory_concurrent_flows=None,
    ):
        """Setup generator and return connected instance."""

        assert core_count >= 3, "Minimum number of allowed CPU cores is 3."

        generator = self._prepare_generator(
            request,
            interface_count,
            core_count,
            specific_cores,
        )

        cfg = setup_cfg_file(
            request,
            generator,
            generator.get_cores(),
            role,
            memory_mb,
            memory_concurrent_flows,
        )

        for cnt in range(self.STARTUP_ATTEMPTS):
            try:
                return trex_class().connect(
                    request,
                    generator,
                    cfg,
                    request.config.getoption("trex_force_use"),
                )
            except TRexZMQPortsUsedError:
                if cnt >= self.STARTUP_ATTEMPTS - 1:
                    raise
                elif generator.get_zmq_pub_port() or generator.get_zmq_rpc_port():
                    raise
                else:
                    global_logger.info(
                        f"TRex startup failed due to ZMQ port being used by another "
                        "process. Will try again with different ports "
                        f"({self.STARTUP_ATTEMPTS - 1 - cnt} retries left)."
                    )
                    randomize_ports(request, generator, cfg)
                    continue

    def _prepare_generator(
        self,
        request,
        interface_count,
        core_count,
        specific_cores,
    ):
        """Find suitable generator in a pool of generators.
        Register finalizer to free a generator.
        """

        for machine in self._pool.get_machines():
            generator = machine.get_generator(interface_count, core_count, specific_cores)
            if generator is not None:

                def cleanup():
                    machine.free_generator(generator)

                request.addfinalizer(cleanup)
                return generator

        cores = specific_cores if specific_cores else core_count

        raise RuntimeError(
            f"TRex generator with {interface_count} interfaces and "
            f"{cores} CPU cores is not available."
        )
