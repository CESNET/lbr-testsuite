# Using TRex traffic generator

This provides examples of using TRex traffic generator to generate SYN flood attack.

### Example of execution (from "examples/trex" directory):

    $ python3.11 -m pytest --trex-generator="trex,0000:65:00.0" -s --log-level=info test_trex_generator.py

This executes test from [test_trex_generator.py](test_trex_generator.py) file. For details (eg.
description of `--trex-generator` parameter) see [TRex documentation](../../lbr_testsuite/trex/README.md).
Test currently expects that target machine already has TRex installed and TRex daemon running.

    $ python3.11 -m pytest --trex-generator="trex,0000:65:00.0" --wired-trex="trex;0000:00:00.0" -s --log-level=info test_trex_generator_topology.py

This executes test from [test_trex_generator_topology.py](test_trex_generator_topology.py) file.
Test uses [topology](../../lbr_testsuite/_pytest_plugins/topology/_trex.py) mechanism to prepare TRex manager.

> **_NOTE:_** Change parameters (hostnames, PCI addresses, target MAC and VLAN) to match your environment.

> **_NOTE:_** Don't forget to install desired version of testsuite, e.g. for
installation from repository just use this from repository root:

    $ python3.11 -m ensurepip
    $ python3.11 -m pip install .
