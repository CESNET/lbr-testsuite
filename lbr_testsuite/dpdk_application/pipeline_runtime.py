"""
Author(s):
    Kamil Vojanec <vojanec@cesnet.cz>
    Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Define interface for accessing pipeline runtime of (DPDK) application.
"""

from abc import ABC, abstractmethod


class PipelineRuntime(ABC):
    """Interface for accessing pipeline runtime."""

    @abstractmethod
    def get_pid(self):
        pass

    @abstractmethod
    def get_pipeline_names(self) -> list[str]:
        pass

    @abstractmethod
    def get_replica_worker_status(self, replica_id: int, worker_idx: int = 0, name: str = None):
        """Obtain the status of a worker within the specified replica.

        Parameters
        ----------
        replica_id: int
            Numerical ID (starting from 0) of a replica in the selected pipeline.
        worker_idx: int, optional, default=0
            Index of the worker in the specified replica. If not specified, the default
            is the first worker - this corresponds to pipelines with no vertical scaling.
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def get_replicas_count(self, name: str = None):
        """Obtain the count of replicas in the selected pipeline.

        Parameters
        ----------
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def get_replica_workers_count(self, replica_id: int, name: str = None):
        """Obtain count of workers of the given replica in the selected pipeline.

        Parameters
        ----------
        replica_id: int
            ID of the selected replica.
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def get_pipeline_stage_names(self, name: str = None) -> list[str]:
        """Obtain list of stage names of the selected pipeline.

        Parameters
        ----------
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def wait_until_active(self, timeout=5):
        pass

    @abstractmethod
    def get_replica_worker_chain_status(
        self,
        replica_id: int,
        worker_idx: int = 0,
        name: str = None,
    ) -> dict:
        """Obtain the chain status of a worker within the specified replica.

        Parameters
        ----------
        replica_id: int
            Numerical ID (starting from 0) of a replica in the selected pipeline.
        worker_idx: int, optional, default=0
            Index of the worker in the specified replica. If not specified, the default
            is the first worker - this corresponds to pipelines with no vertical scaling.
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """Obtain pipeline's statistics across all ports.

        Returns
        -------
        dict
            Dictionary with aggregated port statistics.

        """

        pass

    @abstractmethod
    def get_xstats(self) -> dict:
        """Obtain pipeline's extended statistics across all ports.

        Returns
        -------
        dict
            Dictionary with aggregated port statistics.

        """

        pass

    @abstractmethod
    def get_mempool_stats(self) -> list[dict]:
        """Obtain statistics of mempools in the underlying application if any.
        Each mempool is identified by a unique name.

        Returns
        -------
        list
            List of mempool statistics (each is a directory).
        """

        pass

    def get_sys_if(self) -> str:
        """Obtain the system interface name for the given pipeline.
        For pipelines that do not define their own system interfaces,
        this method provides a default value "<unknown>".

        Returns
        -------
        str
            System interface name
        """

        return "<unknown>"
