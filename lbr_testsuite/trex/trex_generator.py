"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET

Implementation of topology generators for TRex traffic generator.

Module contains 3 classes:

TRexGenerator - represents one TRex generator. It consists of host, ports
and control daemon.

TRexMachine - represents one physical machine. It can provide multiple TRex
generators - for example, machine with 4 ports can provide up to 4 single-port
generators or 2 double-port generators.

TRexMachinesPool - provides pool of TRex machines (TRexMachine). This is a utility
class and it's main purpose is to keep compatibility with current implementation of
Topology. Topology requires one ``Device`` and one ``Generator`` object, but TRex
topology can work with multiple generators. Class TRexMachinesPool solves it by being
one ``Generator``-like object while providing means to obtain multiple TRex generators.
If Topology allows multiple ``Generator`` objects in the future, then this class loses
it's purpose and can be removed.
"""

import lbr_trex_client  # noqa: F401
from trex_client import CTRexClient

from ..topology.generator import Generator
from ..topology.pci_address import PciAddress


class TRexGenerator(Generator):
    """Class represents TRex generator.

    Parameters
    ----------
    host : str
        Host where TRex is installed. Can be hostname or IP address.
    interfaces : list(str)
        PCI addresses of network interfaces.
    cores : list(int)
        CPU cores to use.
    daemon : CTRexClient
        TRex daemon running on ``host``.
        Daemon controls start and termination of one TRex instance.
    """

    def __init__(self, host, interfaces, cores, daemon):
        self._host = host
        self._interfaces = interfaces
        self._cores = cores
        self._daemon = daemon

    def get_host(self):
        """Return TRex host.

        Returns
        -------
        str
            TRex host.
        """

        return self._host

    def get_interfaces(self):
        """Return PCI addresses of an interfaces.

        Returns
        -------
        list(str)
            PCI addresses of an interfaces.
        """

        return self._interfaces

    def get_cores(self):
        """Return used CPU cores.

        Returns
        -------
        list(int)
            CPU cores.
        """

        return self._cores

    def get_daemon(self):
        """Return daemon.

        Daemon is connected and ready to start or
        terminate TRex instance.

        Returns
        -------
        trex_client.CTRexClient
            Daemon object.
        """

        return self._daemon

    def invalidate(self):
        """Invalidate this generator."""

        self._host = None
        self._interfaces = None
        self._cores = None
        self._daemon = None


class TRexMachine:
    """Class represents TRex machine.

    Parameters
    ----------
    host : str
        TRex host. Can be hostname or IP address.
    interfaces : list(str)
        PCI addresses of network interfaces.
    """

    # This will be replaced by connecting to the
    # machine and retrieving actual CPU core count
    _CPU_CORES = 20

    def __init__(self, host, interfaces):
        self._host = host
        self._interfaces = interfaces
        self._daemons = list()
        self._available_cores = list(range(self._CPU_CORES))

        # ports configured by ansible playbook
        for port in [8090, 8091, 8092, 8093]:
            self._daemons.append(
                CTRexClient(
                    trex_host=host,
                    trex_daemon_port=port,
                    master_daemon_port=None,
                    trex_zmq_port=None,
                )
            )

    def get_host(self):
        """Return TRex host.

        Returns
        -------
        str
            TRex host.
        """

        return self._host

    def get_generator(self, ifc_count=1, core_count=6):
        """Get TRex generator.

        Parameters
        ----------
        ifc_count : int, optional
            Number of interfaces.
        core_count : int, optional
            Number of CPU cores.

        Returns
        -------
        TRexGenerator or None
            TRex generator if available.
            None if generator with ´´ifc_count´´ interfaces
            and ´´core_count´´ cores is not available.
        """

        if ifc_count > len(self._interfaces):
            return None

        if core_count > len(self._available_cores):
            return None

        if len(self._daemons) < 1:
            return None

        daemon = self._daemons.pop()
        interfaces = [self._interfaces.pop(0) for _ in range(ifc_count)]
        cores = [self._available_cores.pop(0) for _ in range(core_count)]

        return TRexGenerator(self._host, interfaces, cores, daemon)

    def free_generator(self, generator):
        """Free TRex generator.

        Parameters
        ----------
        generator : TRexGenerator
            Genererator returned by ´´get_generator´´ method.
        """

        assert generator.get_host() == self._host, "Generator from different host"

        self._daemons.append(generator.get_daemon())
        self._interfaces.extend(generator.get_interfaces())
        self._available_cores.extend(generator.get_cores())
        generator.invalidate()


class TRexMachinesPool(Generator):
    """Class manages pool of TRex machines.

    This is class satisfies ``Generator`` object required by
    Topology while managing multiple TRex machines.

    Parameters
    ----------
    host_data : dict(str, list)
        Dict contaning host as key and list of PCI addresses as value.
        Example:
        {
            "trex.liberouter.org": ["0000:65:00.0", "0000:65:00.1"],
            "trex2.liberouter.org": ["0000:65:00.0", "0000:b3:00.0"],
        }
    """

    def __init__(self, host_data):
        self._trex_machines = []

        for host, interfaces in host_data.items():
            for ifc in interfaces:
                assert PciAddress.is_valid(ifc)

            self._trex_machines.append(TRexMachine(host, interfaces))

    def get_machines(self):
        """Return list of TRex machines.

        Returns
        -------
        list(TRexMachine)
            List of available TRex machine.
        """

        return self._trex_machines
