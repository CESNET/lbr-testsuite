"""
Author(s):  Jan Sobol <sobol@cesnet.cz>
            Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Simple TRex module example using topology. It generates SYN flood traffic.

For your environment, set correct TARGET_VLAN and TARGET_MAC variables.

Example usage:
    pytest --trex-generator="trex,0000:65:00.0" --wired-trex="trex;0000:01:00.0" -s --log-level=info
"""

import pprint

import pytest

from lbr_testsuite import trex
from lbr_testsuite.topology.topology import select_topologies


TARGET_VLAN = 25
TARGET_MAC = "b8:59:9f:e2:09:f6"
FLOOD_DURATION = 10


select_topologies(["wired_trex"])


def test_trex_syn_flood_topology(request: pytest.FixtureRequest, trex_manager: trex.TRexManager):
    attacker = trex_manager.request_stateless(request)
    attacker.set_vlan(TARGET_VLAN)
    attacker.set_dst_mac(TARGET_MAC)

    # Acquire ports, clear stats
    attacker.reset()

    syn_flood = trex.TRexStream(
        l3="ipv4",
        l4="tcp",
        l3_src="200.0.0.0/24",
        l3_dst="100.0.0.0/24",
        l4_src=(1, 65535),
        l4_dst=80,
        pkt_len=100,
        rate="1Mpps",
        vlan_id=TARGET_VLAN,
    )
    attacker.add_stream(syn_flood)

    attacker.start(duration=FLOOD_DURATION)
    attacker.wait_on_traffic()

    stats = attacker.get_stats()
    print("\nTRex statistics:\n")
    pprint.pprint(stats, sort_dicts=False, underscore_numbers=True)

    tx_attack_packets = stats["total"]["opackets"]
    expected_tx_attack = FLOOD_DURATION * 1_000_000  # 1Mpps

    # 1 packet upper tolerance
    assert expected_tx_attack <= tx_attack_packets <= expected_tx_attack + 1, (
        "TRex did not generate expected number of packets. "
        f"Expected: {expected_tx_attack}, generated: {tx_attack_packets}."
    )
