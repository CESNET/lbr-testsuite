"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2023 CESNET, z.s.p.o.

Module implements TRex manager class.

Manager provides TRex generator upon request.
"""

import logging

from .trex_base import TRexZMQPortsUsedError
from .trex_configuration_file import randomize_ports, setup_cfg_file
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

        Returns
        -------
        TRexStateless
            TRexStateless if request was successful.
        """

        return self._request_generator(
            request,
            interface_count,
            core_count,
            TRexStateless,
        )

    def request_stateful(
        self,
        request,
        role,
        core_count=6,
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
            TRexAdvancedStateful,
            role,
        )

    def _request_generator(
        self,
        request,
        interface_count,
        core_count,
        trex_class,
        role=None,
    ):
        """Setup generator and return connected instance."""

        assert core_count >= 3, "Minimum number of allowed CPU cores is 3."

        generator = self._prepare_generator(
            request,
            interface_count,
            core_count,
        )

        cfg = setup_cfg_file(
            request,
            generator,
            generator.get_cores(),
            role,
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
    ):
        """Find suitable generator in a pool of generators.
        Register finalizer to free a generator.
        """

        for machine in self._pool.get_machines():
            generator = machine.get_generator(interface_count, core_count)
            if generator is not None:

                def cleanup():
                    machine.free_generator(generator)

                request.addfinalizer(cleanup)
                return generator

        raise RuntimeError(
            f"TRex generator with {interface_count} interfaces and "
            f"{core_count} CPU cores is not available."
        )
