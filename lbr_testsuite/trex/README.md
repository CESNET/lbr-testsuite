# Module trex

Module contains **custom** components for working with [TRex traffic generator](https://trex-tgn.cisco.com/).
Main high-level component is [TRex Manager](./trex_manager.py).
Upon request, manager can provide handler to running TRex.
TRex can be started in either stateless (STL) or advanced stateful (ASTF) mode.

Handler has simplified API for working with TRex.
User can always access official handler object via `get_handler()` method to work
with official API.

##### Example

```python
small_attacker = trex_manager.request_stateless(request)
big_attacker = trex_manager.request_stateless(request, interface_count=2, core_count=16)

client = trex_manager.request_stateful(request, role="client")
server = trex_manager.request_stateful(request, role="server")
```

#### Stateless API

Stateless mode generates packets based on Scapy template and Field Engine instructions.
Traffic is defined via streams. Streams are loaded into TRex and can be used to generate packets.
For details see [trex_stateless](./trex_stateless.py) and [trex_base](./trex_base.py).

##### Example

Generate simple traffic pattern using the previously requested `small_attacker`.

```python
attacker_traffic=TRexStream(
    l2_dst="AA:BB:CC:DD:EE:FF",
    vlan_id=100,
    l3="ipv4",
    l4="tcp",
    l3_src="10.0.100.0/24",
    l3_dst="10.0.1.0/26",
    l4_src=(1, 65500),
    l4_dst=80,
    pkt_len=100,
    rate="1Mpps",
    mode_selector=TRexStreamModeSelector.CONTINUOUS,
)

small_attacker.add_stream(attacker_traffic)
small_attacker.start(duration=10)
small_attacker.wait_on_traffic()

print(small_attacker.get_stats())
```

#### Advanced Stateful API

Advanced Stateful mode generates stateful traffic using TRex's own TCP stack (based on FreeBSD). It can act
like a real host on network (eg. initiates/accepts TCP connection, responds to
TCP flags, retransmits lost/mitigated packets and so on). Traffic is defined via
profiles. Profiles are loaded into TRex and then can be generated. Main part of
profile is traffic program. Program uses [official TRex API](https://trex-tgn.cisco.com/trex/doc/cp_astf_docs/api/profile_code.html#astfprogram-class).
For rest of details see [trex_stateful](./trex_stateful.py) and [trex_base](./trex_base.py).

##### Example

Create a simple stateful client-server pair with provided traffic program and generate traffic between them.

```python
def http():
    """Define HTTP traffic template for Advanced Stateful TRex generator."""

    http_req = b"GET /3384 HTTP/1.1\r\n..."
    http_response = "HTTP/1.1 200 OK\r\n..."

    # Client
    prog_c = ASTFProgram(side="c")
    prog_c.connect()
    prog_c.send(http_req)
    prog_c.recv(len(http_response))
    # Implicit TCP termination from client

    # Server
    prog_s = ASTFProgram(side="s")
    prog_s.accept()
    prog_s.recv(len(http_req))
    prog_s.send(http_response)
    prog_s.wait_for_peer_close()

    return (prog_c, prog_s)

http_traffic = TRexProfile(
    program=http(),
    client_net="99.0.0.0/24",
    server_net="100.0.0.0/26",
    l4_dst=80,
    conn_rate=1000,
)

client.set_dst_mac(server.get_src_mac())
server.set_dst_mac(client.get_src_mac())
client.load_profile(http_traffic)
server.load_profile(http_traffic)

server.start()
client.start(duration=10)
client.wait_on_traffic()
server.stop()

print(client.get_stats())
print(server.get_stats())
```

## Setting up TRex for TRex Manager

#### TRex daemon

TRex manager needs to start and terminate TRex process on given machine upon request.
For these operations it requires TRex daemon(s). Daemon is provided by standard TRex installation.
Currently, 4 daemons are supported on ports 8090-8093. One daemon can manage only one TRex process.
This means TRex Manager can currently provide **only 4 generators** on request. This can be
increased in the future if needed.

To start these daemons, go to TRex directory on given machine and run following commands:

```shell
./master_daemon.py --type trex_daemon_server --trex-daemon-port 8090 start
./master_daemon.py --type trex_daemon_server --trex-daemon-port 8091 start
./master_daemon.py --type trex_daemon_server --trex-daemon-port 8092 start
./master_daemon.py --type trex_daemon_server --trex-daemon-port 8093 start
```

Note that ports need to be available for remote connections (not hidden behind **firewall**).

#### Configuration file
TRex requires configuration file during startup. It defines CPU cores, memory, **network interfaces** etc..
Some can be adjusted automatically, but user needs to
provide which network interfaces can be used by TRex.

When using `pytest`, importing `lbr-testsuite` provides various [TRex options/fixtures](../_pytest_plugins/topology/_trex.py).
Option `--trex-generator` specifies single TRex generator. It consists of hostname and
PCI address of interface (separated by a comma). Here is example of two machines, each machine having two
usable network interfaces for TRex:

```shell
--trex-generator='trex-machine1.company.xyz,0000:b3:00.0' \
--trex-generator='trex-machine1.company.xyz,0000:b3:00.1' \
--trex-generator='trex-machine2.company.xyz,0000:65:00.0' \
--trex-generator='trex-machine2.company.xyz,0000:65:00.1'
```

For TRex Manager this provides a pool of 4 available interfaces. When requesting stateless
generator, user can specify parameter `interface_count`. Manager will then consume _N_
interfaces from the pool to provide one generator with _N_ interfaces.

Configuration file is automatically created (based on these options) and uploaded to
TRex machine. Some parameters, such as memory, are currently fixed and can't be changed.
Minimum amount of memory (hugepages) is 2048 MB per interface. Minimum amount of
CPU cores per generator is 3.

#### Initialization

When using `pytest`, importing `lbr-testsuite` also provides `trex_generators` fixture.
This fixture provides parsed `--trex-generator` options. It should be used to initialize
TRex Manager. Here is example of initialization implemented as a pytest fixture:

```shell
$ pytest --trex-generator='trex-machine1.company.org,0000:b3:00.0' ...
```

```python
@pytest.fixture
def trex_manager_init(trex_generators):
    pool = TRexMachinesPool(trex_generators)
    return TRexManager(pool)
```

##### Note on topology

Package `lbr-testsuite` contains so-called [topologies](../_pytest_plugins/topology/).
One of them is TRex topology. When using TRex topology, fixture `trex_manager` is available
and provides initialized TRex Manager. However, topologies are complex topic and
won't be described here.

#### Ansible playbook

TRex Manager also provides `run_ansible_playbook` method. It can configure machine
via supplied Ansible playbook. For example, it could be used to download and install
TRex on machine, set up hugepages and start TRex daemons. Playbook is not provided by
`lbr-testsuite`.

#### TRex Manager Diagram

![image](README_TRex_manager.svg "TRex Manager Diagram")

## Complete example of SYN flood

```shell
$ pytest --trex-generator='trex-machine1.company.org,0000:b3:00.0' \
         --trex-generator='trex-machine1.company.org,0000:b3:00.1' \
         --trex-generator='trex-machine1.company.org,0000:65:00.0'
```

```python
import pytest
from lbr_testsuite import trex
from lbr_testsuite.trex.trex_stateless import TRexL4Flag
from trex.astf.trex_astf_profile import ASTFProgram

def test_trex_example(request: pytest.FixtureRequest, trex_generators: dict):
    trex_manager = trex.TRexManager(trex.TRexMachinesPool(trex_generators))

    attacker = trex_manager.request_stateless(request)
    client = trex_manager.request_stateful(request, role="client")
    server = trex_manager.request_stateful(request, role="server")

    attacker.get_handler().set_verbose("info")
    client.get_handler().set_verbose("info")
    server.get_handler().set_verbose("info")

    attacker_traffic=trex.TRexStream(
        l3="ipv4",
        l4="tcp",
        l3_src="10.0.100.0/24",
        l3_dst="10.0.1.0/26",
        l4_dst=80,
        rate="100kpps",
        l4_flags=TRexL4Flag.SYN,
    )
    attacker.reset()
    attacker.set_dst_mac(server.get_src_mac())
    attacker.add_stream(attacker_traffic)

    def tcp_connection():
        prog_c = ASTFProgram(side="c")
        prog_c.connect()
        prog_s = ASTFProgram(side="s")
        prog_s.accept()
        prog_s.wait_for_peer_close()
        return (prog_c, prog_s)

    tcp_traffic = trex.TRexProfile(
        program=tcp_connection(),
        client_net="99.0.0.0/24",
        server_net="10.0.1.0/26",
        l4_dst=80,
        conn_rate=1000,
    )

    client.reset()
    server.reset()
    client.set_dst_mac(server.get_src_mac())
    server.set_dst_mac(client.get_src_mac())
    client.load_profile(tcp_traffic)
    server.load_profile(tcp_traffic)

    server.start()
    client.start(duration=10)
    attacker.start(duration=10)
    client.wait_on_traffic()
    attacker.wait_on_traffic()
    server.stop()

    print(attacker.get_stats())
    print(client.get_stats())
    print(server.get_stats())
```
