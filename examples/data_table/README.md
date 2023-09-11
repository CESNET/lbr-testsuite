# Throughput measurements with CSV tables and charts creation.

This example presents usage of data_table module for throughput measurements.
Tests simulates measuring of throughput for selected packet lengths. Simple
test case does not use any additional parameters and simply measures throughput
for defined packet lengths. Complex case adds parametrization to tests and
presents how same measurements for different setup can be done.

Tests actually does not measure anything. It uses predefined test values as
mocked measurements.

### Example of execution (from "examples" directory):

    $ pytest -k "charts" --log-level=debug

> **_NOTE:_** With logging level set to debug there are paths to temporary tables (csv)
and charts (png) printed so you can easily access them.

<br/><br/>

> **_NOTE:_** Don't forget to install desired version of testsuite, e.g. for
installation from repository just use this from repository root:

    $ pip install .
