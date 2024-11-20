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
    def get_worker_status(self, worker_id: int, name: str = None):
        """Obtain worker's status in the selected pipeline.

        Parameters
        ----------
        worker_id: int
            Numerical ID (starting from 0) of a worker in the selected pipeline.
        name : str, optional
            Name of the pipeline (default is the first pipeline).
        """

        pass

    @abstractmethod
    def get_workers_count(self, name: str = None):
        """Obtain count of workers of the selected pipeline.

        Parameters
        ----------
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
    def get_worker_chain_status(self, worker_id: int, name: str = None) -> dict:
        """Obtain worker's chain status in the selected pipeline.

        Parameters
        ----------
        worker_id: int
            Numerical ID (starting from 0) of a worker in the selected pipeline.
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
