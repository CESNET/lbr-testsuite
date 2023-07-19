"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2022-2023 CESNET, z.s.p.o.

Common sources for packet crafter unit tests.
"""


def _is_equal(a, b):
    """Return True if *unsorted* lists are equal (contain same packets).

    Scapy packets are not hashable, so comparison using set() cannot be done.
    Scapy packets are not sortable (sort based on what layer? which layer gets
    sorted first?), so comparison using sorted() cannot be done.
    """

    if len(a) != len(b):
        return False

    b2 = list(b)
    for item_a in a:
        for item_b in b2:
            if item_b == item_a:
                b2.remove(item_b)
                continue

    if len(b2) == 0:
        return True
    else:
        return False
