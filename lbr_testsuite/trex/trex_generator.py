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

import copy

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
    interfaces : list(tuple(str,int))
        List of network interfaces.
        Each interface is set as tuple, where
        first item is PCI address and second
        item is NUMA node.
    cores : list(int)
        CPU cores to use.
    daemon : CTRexClient
        TRex daemon running on ``host``.
        Daemon controls start and termination of one TRex instance.
    zmq_pub_port : int, optional
        ZMQ Publisher port.
    zmq_rpc_port : int, optional
        ZMQ Remote Procedure Call port.
    """

    def __init__(
        self,
        host,
        interfaces,
        cores,
        daemon,
        zmq_pub_port=None,
        zmq_rpc_port=None,
    ):
        self._host = host
        self._interfaces = interfaces
        self._cores = cores
        self._daemon = daemon
        self._zmq_pub_port = zmq_pub_port
        self._zmq_rpc_port = zmq_rpc_port

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
        list(tuple(str,int))
            List of network interfaces.
            Each interface is set as tuple, where
            first item is PCI address and second
            item is NUMA node.
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

    def get_zmq_pub_port(self):
        """
        Returns
        -------
        int or None
            ZMQ Publisher port.
        """

        return self._zmq_pub_port

    def get_zmq_rpc_port(self):
        """
        Returns
        -------
        int or None
            ZMQ Remote Procedure Call port.
        """

        return self._zmq_rpc_port

    def invalidate(self):
        """Invalidate this generator."""

        self._host = None
        self._interfaces = None
        self._cores = None
        self._daemon = None
        self._zmq_pub_port = None
        self._zmq_rpc_port = None


class TRexMachine:
    """Class represents TRex machine.

    Parameters
    ----------
    host : str
        TRex host. Can be hostname or IP address.
    interfaces : list(tuple(str,int))
        List of network interfaces.
        Each interface is set as tuple, where
        first item is PCI address and second
        item is NUMA node.
    cores : list(int), optional
        CPU cores available on machine.
        If not set, predefined cores will be used.
    zmq_ports : list(int), optional
        List of ZMQ ports to use.
        If not set, random ZMQ ports will be used.
    """

    # This will be replaced by connecting to the
    # machine and retrieving actual CPU core count
    _CPU_CORES = 20

    def __init__(self, host, interfaces, cores=None, zmq_ports=None):
        self._host = host
        self._interfaces = interfaces
        self._daemons = list()
        if cores:
            self._available_cores = cores
        else:
            self._available_cores = list(range(self._CPU_CORES))
        self._zmq_ports = zmq_ports

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

    def get_generator(self, ifc_count=1, core_count=6, specific_cores=[]):
        """Get TRex generator.

        Parameters
        ----------
        ifc_count : int, optional
            Number of interfaces.
        core_count : int, optional
            Number of CPU cores.
            Ignored if "specific_cores" is provided.
        specific_cores : list, optional
            List of specific cores to use instead of "core_count".

        Returns
        -------
        TRexGenerator or None
            TRex generator if available.
            None if generator with ´´ifc_count´´ interfaces
            and ´´core_count´´ cores is not available.
        """

        if ifc_count > len(self._interfaces):
            return None

        if not specific_cores:
            if core_count > len(self._available_cores):
                return None
        else:
            if len(specific_cores) > len(self._available_cores):
                return None
            if set(specific_cores) & set(self._available_cores) != set(specific_cores):
                return None

        if len(self._daemons) < 1:
            return None

        daemon = self._daemons.pop()
        interfaces = [self._interfaces.pop(0) for _ in range(ifc_count)]
        if not specific_cores:
            cores = [self._available_cores.pop(0) for _ in range(core_count)]
        else:
            cores = specific_cores
            for c in cores:
                self._available_cores.remove(c)

        if self._zmq_ports:
            zmq_pub_port = self._zmq_ports.pop(0)
            zmq_rpc_port = self._zmq_ports.pop(0)
        else:
            zmq_pub_port = None
            zmq_rpc_port = None

        return TRexGenerator(self._host, interfaces, cores, daemon, zmq_pub_port, zmq_rpc_port)

    def free_generator(self, generator):
        """Free TRex generator.

        Parameters
        ----------
        generator : TRexGenerator
            Genererator returned by ´´get_generator´´ method.
        """

        assert generator.get_host() == self._host, "Generator from different host"

        self._daemons.append(generator.get_daemon())
        self._interfaces = generator.get_interfaces() + self._interfaces
        self._available_cores = generator.get_cores() + self._available_cores
        self._available_cores.sort()

        if generator.get_zmq_rpc_port():
            self._zmq_ports.insert(0, generator.get_zmq_rpc_port())

        if generator.get_zmq_pub_port():
            self._zmq_ports.insert(0, generator.get_zmq_pub_port())

        generator.invalidate()


class TRexMachinesPool(Generator):
    """Class manages pool of TRex machines.

    This is class satisfies ``Generator`` object required by
    Topology while managing multiple TRex machines.

    Parameters
    ----------
    host_data : dict(str, list)
        Dict contaning host as key and list of tuples (PCI address, numa) as value.
        Example:
        {
            "trex.liberouter.org": [("0000:65:00.0",0), ("0000:65:00.1",0)],
            "trex2.liberouter.org": [("0000:65:00.0",0), ("0000:b3:00.0",0)],
        }
    host_options : dict(str, list), optional
        Dict contaning host as key and dict of additional parameters.
        Example:
        {
            "trex.liberouter.org": {
                "cores": [0,1,2,3,4,5,12,13,14,15,16,17,24],
                "zmq_ports": [4500,4501],
            },
            "trex2.liberouter.org": {
                "cores": [0,1,2,3,4,5,6,7,8,9,10,11],
                "zmq_ports": [4502,4503],
            },
        }
    """

    def __init__(self, host_data, host_options=None):
        self._trex_machines = []
        host_data = copy.deepcopy(host_data)

        for host, interfaces in host_data.items():
            for ifc, numa in interfaces:
                assert PciAddress.is_valid(ifc)

            cores = None
            zmq_ports = None

            if host_options:
                host_options = copy.deepcopy(host_options)
                if host in host_options:
                    cores = host_options[host].get("cores")
                    zmq_ports = host_options[host].get("zmq_ports")

            self._trex_machines.append(TRexMachine(host, interfaces, cores, zmq_ports))

    def get_machines(self):
        """Return list of TRex machines.

        Returns
        -------
        list(TRexMachine)
            List of available TRex machine.
        """

        return self._trex_machines
