"""
Author(s):
    Kamil Vojanec <vojanec@cesnet.cz>
    Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2024 CESNET, z.s.p.o.

Define interface for accessing pipeline runtime of (DPDK) application.
"""


class PipelineRuntime:
    """Interface for accessing pipeline runtime."""

    def get_pid(self):
        pass

    def get_pipeline_names(self) -> list[str]:
        pass

    def get_worker_status(self, worker_id):
        pass

    def get_workers_count(self):
        pass

    def get_pipeline_stage_names(self) -> list[str]:
        pass

    def wait_until_active(self, timeout=5):
        pass

    def get_worker_chain_status(self, worker_id) -> dict:
        pass
