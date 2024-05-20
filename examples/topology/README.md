# Topology usage

Demonstration of topology usage. Test prints information about
used device, generator and analyzer. The conftest.py file implements
example topology that requires device, generator and analyzer.

### Example of execution (from "examples/topology" directory):

    $ pytest --vdevs -s

This executes test with virtual devices topology. It should work on any machine.

    $ pytest --vdevs --wired-loopback=0000:05:00.0,0000:05:00.1 -s

This executes test with virtual devices topology and wired loopback topology.
Wired loopback requires real PCI-e addresses of network devices on given machine, otherwise
it ends with error.

    $ pytest --vdevs --example-topology=0000:05:00.0,0000:06:00.0,0000:06:00.1,0000:05:00.1 -s

This executes test with example topology implemented in conftest.py file.
Just like wired loopback it requires real PCI-e addresseses.

> **_NOTE:_** Don't forget to install desired version of testsuite, e.g. for
installation from repository just use this from repository root:

    $ pip install .
