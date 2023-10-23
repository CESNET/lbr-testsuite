"""
Author(s): Pavel Krobot <Pavel.Krobot@cesnet.cz>

Copyright: (C) 2020-2023 CESNET, z.s.p.o.

Helper class for VLAN configuration management.

VLAN configuration depends on machine(s) used and their interconnection.
Typically for local loobpack there is no special configuration needed.
However, machines connected via switch often have various VLANs
configured.

Short VLAN behavior description
-------------------------------
Switch ports typically have some access VLAN ID and some range of trunk
VLAN IDs assigned. If traffic with no VLAN tag is received on such
port, it is automatically tagged using access VLAN ID. Conversely,
if traffic tagged by access VLAN is sent out of an access port, the VLAN
is stripped.

Traffic tagged by trunk VLANs is sent as-is. Thus, no VLAN
ID is added or stripped and traffic tagged by such VLAN ID is sent
and received with this VLAN ID.

Traffic tagged by VLAN ID which is not configured as access nor trunk
is dropped.

When to use access, trunk or no VLAN
------------------------------------
No VLAN is used when machines/ports are in same access VLAN.

Trunk VLAN(s) is used when traffic needs to be received with
given VLAN ID. Machines/ports have this VLAN configured as
trunk VLAN.

Access VLAN is used when generated traffic needs to be received
with no VLAN tag but machines are not in same access VLAN.
Generating machine will have this VLAN as trunk VLAN, thus
packets will be forwarded as-is. Receiving machine will have this
VLAN as access VLAN, thus VLAN is stripped when leaving port.
"""


class VLANConfig:
    """VLAN configuration class.

    This class is supposed to hold VLAN configuration. A class instance
    can be initialized with single access VLAN, multiple trunk VLANs or
    both. Trunk VLAN IDs are managed using a dictionary. This dictionary is
    build as trunk VLAN IDs are requested. If a key is not associated
    with any VLAN ID, new association is created using given key and list
    of available trunk VLAN IDs. This allows caller to use same
    trunk VLAN ID from different points of a test using same key.

    e.g. Having VLANConfig instance initialized with two trunk VLAN IDs:

    vc = VLANConfig(trunk_vlans=[10,20])

    One can use first VLAN ID for client and second for server:

    def func_client(vc):
        config_vlan(vc.acquire_trunk_vlan('client'))

    def func_server(vc):
        config_vlan(vc.acquire_trunk_vlan('server'))

    ...

    print(vc.acquire_trunk_vlan('client')) #prints same VLAN used in func_client
    print(vc.acquire_trunk_vlan('server')) #prints same VLAN used in func_server

    Attributes
    ----------
    _access : int
        VLAN ID of access VLAN (None if not used).
    _trunks : list(int)
        List of trunk VLAN IDs. If not initialized to any specific VLAN
        IDs, default range of VLAN IDs from 1 to 4094 is used. Usage of
        default trunk VLAN IDs makes sense in scenarios where there are
        no special requirements for connection (mostly local loopback).
    _trunks_used : int
        Number of trunk VLAN IDs used from _trunks list. _trunks_used
        equal to length of _trunks means no more trunk VLAN IDs
        available.
    _trunks_mapping : dict()
        Dictionary holding mapping of trunk VLAN IDs to keys. Keys are
        arbitrary and defined by using a key for a first time in
        acquire_trunk_vlan() method.
    """

    def __init__(self, access_vlan=None, trunk_vlans=None):
        """
        Parameters
        ----------
        access_vlan : int, optinal
            VLAN ID of access VLAN.
        trunk_vlans : list(int), optional.
            List of trunk VLAN IDs.
        """

        self._access = access_vlan
        self._trunks = trunk_vlans
        self._trunks_used = 0
        self._trunks_mapping = dict()

        if not self._trunks:
            self._trunks = list(range(1, 4095))
            if self._access:
                # remove access VLAN ID from trunks
                self._trunks.remove(self._access)

    def access_vlan(self):
        """Access VLAN ID getter.

        Returns
        -------
        int or None
            Access VLAN ID or None if VLAN not set.
        """

        return self._access

    def acquire_trunk_vlan(self, key=None):
        """Method for trunk VLAN ID obtaining.

        VLAN ID is selected from trunk VLAN IDs mapping or if
        the mapping does not exists it creates new using the key and
        VLAN ID from _trunks.

        Parameters
        ----------
        key : an immutable data type
            Key used for access to trunk VLAN ID. If no VLAN ID assigned
            to an ID, new association is made.

        Returns
        -------
        int
            Trunk VLAN ID associated with given key.
        """

        if not key:
            key = str(self._trunks_used)

        if key not in self._trunks_mapping:
            assert self._trunks_used < len(self._trunks), "No more trunk VLANs available."
            self._trunks_mapping[key] = self._trunks[self._trunks_used]
            self._trunks_used += 1

        return self._trunks_mapping[key]
