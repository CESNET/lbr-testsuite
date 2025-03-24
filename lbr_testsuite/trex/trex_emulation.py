"""
Author(s): Dominik Tran <tran@cesnet.cz>

Copyright: (C) 2025 CESNET, z.s.p.o.

Module implements Emulation TRex generator class.

Emulation mode (EMU) runs on top of stateless mode.
It implements various protocols (in form of plugins)
to process and generate traffic.

EMU is implemented in Go and the workflow is different
compared to stateless or ASTF mode (C++). This is reflected
in Python API as well.

Due to differences between supported protocols, ranging
from L2 ARP to L7 protocols like DNS and
DHCP, this module doesn't implement its own
profile/stream dataclass like STL and ASTF modules.

There is only "load_profile" function, which loads
given EMU Profile. See official documentation for details
on EMU profile:
https://trex-tgn.cisco.com/trex/doc/trex_emu.html
https://trex-tgn.cisco.com/trex/doc/cp_emu_docs/index.html
"""

import os
import pathlib

import lbr_trex_client  # noqa: F401
import trex.stl.trex_stl_client as trex_stl_client
import yaml
from trex.common.trex_client import ALL_MASK
from trex.emu.trex_emu_client import EMUClient


class TRexEmulation:
    """Emulation TRex generator class.

    Emulation mode runs on top of stateless mode.
    It implements various protocols (in form of plugins)
    to process and generate traffic.

    Warning: Due to currently hardwired listening port (
    4510), only one active instance of TRexEmulation will work.
    """

    _lock = False

    def __init__(self):
        self._handler = None
        self._daemon = None

    def connect(self, request, generator, conf_file, force=False):
        """Connect to TRex.

        Execute following steps:
            1) Connect to TRex daemon.
                Daemon is launched when TRex machine is configured with Ansible playbook.
            2) Start EMU TRex via daemon.
                Daemon can start and stop only one TRex instance.
            3) Set port to promiscious mode to accept all packets.
                This lets software/EMU plugins to do the filtering.
            4) Set port to service "filtered" mode and set mask for all packets.
                When using more than a single CPU core, EMU won't work
                properly without this setting.
            5) Return handler to connected EMU TRex.

        Parameters
        ----------
        request : fixture
            Special pytest fixture, here used for finalizer.
        generator : TRexGenerator
            TRex generator object.
        conf_file : str
            Path to configuration file (on local machine).
        force : bool, optional
            If True, kill previous instance if it's running before starting TRex.

        Returns
        -------
        TRexEmulation
            Connected TRex.
        """

        if TRexEmulation._lock and not force:
            raise RuntimeError("Only one instance of TRexEmulation is supported")

        self._daemon = generator.get_daemon()
        # Assemble path to configuration file on TRex machine
        remote_cfg_file = pathlib.Path(
            self._daemon.get_trex_files_path(), os.path.basename(conf_file)
        )

        if force:
            self._daemon.force_kill(confirm=False)

        with open(conf_file, "r") as f:
            cfg = yaml.safe_load(f)

        self._handler = self._start_trex(
            generator.get_host(),
            remote_cfg_file,
        )

        self._handler.connect()
        request.addfinalizer(self.terminate)

        # EMUClient has limited set of supported
        # operations, so we must connect to underlying
        # stateless TRex and use its handler to set port to
        # promiscious mode and set "filtered" service mode.
        stl_handler = trex_stl_client.STLClient(
            server=generator.get_host(),
            sync_port=cfg[0]["zmq_rpc_port"],
            async_port=cfg[0]["zmq_pub_port"],
        )
        stl_handler.connect()
        stl_handler.reset()
        stl_handler.set_port_attr(promiscuous=True, multicast=True)
        stl_handler.set_service_mode(enabled=False, filtered=True, mask=ALL_MASK)
        stl_handler.disconnect()
        TRexEmulation._lock = True

        return self

    def terminate(self):
        """Terminate TRex.

        Disconnect from TRex, then terminate it via its daemon.
        """

        self._handler.disconnect()
        self._daemon.stop_trex()
        TRexEmulation._lock = False

    def get_handler(self):
        """Get TRex handler that is used by official API.

        Also see TRexBase.get_handler().

        Official documentation link:
            https://trex-tgn.cisco.com/trex/doc/cp_emu_docs/api/index.html

        Returns
        -------
        EMUClient
            Official EMU TRex handler.
        """

        return self._handler

    def _start_trex(self, host, remote_cfg_file):
        """Start TRex and return its handler.

        Internally, Emulation TRex is started in
        stateless mode with few extra options:

        --software makes all RX packets to be processed by software.
        This decreases performance.

        --emu loads EMU server on top of stateless TRex.
        """

        self._daemon.start_stateless(
            cfg=str(remote_cfg_file),
            software=True,
            emu=True,
        )

        # EMU is hardwired to listen at port 4510
        return EMUClient(server=host)

    def load_profile(self, profile, tunables=None):
        """Load EMU traffic profile.

        Parameters
        ----------
        profile : str or EMUProfile
            Path to filename of the EMU traffic profile or a valid EMUProfile object.
        tunables : list(str)
            Parameters specific to given profile.
            Each profile can support different parameters.
            Examples:
            ['--ns', '1', '--clients', '10']
            [
                '--vlan-id', '21',
                '--src-mac', '00:00:00:90:00:01',
                '--dst-mac', '0c:42:a1:22:25:87',
                '--src-ip', '3.3.3.3',
            ]
        """

        self._handler.load_profile(profile, tunables=tunables)
