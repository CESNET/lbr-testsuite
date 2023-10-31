# Python package lbr_testsuite

The purpose of this package is to provide common set of tools
that can be used in development of tests. Package now contains
`common`, `data_table`, `executable`, `ipconfigurer`, `packet_crafter`,
`spirent`, `trex` and `vlan_config`.

The package also includes the `Topology` plugin for pytest. The plugin provides
a set of fixtures and pre-defined pytest arguments that can be used to prepare
a testing environment. The `Topology` plugin is automatically installed into
pytest with the `lbr_testsuite` package.


## Hosting and contribution

Package `lbr_testsuite` is hosted in [PyPI index](https://pypi.org/project/lbr-testsuite/).
You can list all available versions by following this [link](https://pypi.org/project/lbr-testsuite/#history).

This project uses GitLab CI pipeline which is triggered
with every new commit. If coding style (PEP8) check passes, then
pipeline creates .whl package from contents inside [lbr_testsuite](./lbr_testsuite)
folder. This package can be found in `build` step of pipeline and downloaded
for manual installation.

If the pipeline triggers on the `master` branch, the package is also published.
Releases (tagged commits) are uploaded to PyPI, development versions are uploaded
to internal GitLab's Package Registry.
Version of the package is controlled using git tags. Development package names
are composed from current version and the hash of the last commit.

Development of this repository is done mainly through GitLab. The repository is
mirrored to GitHub for the purpose of publishing the code.


## Installation

Install from PyPI index via command:
```
pip install lbr-testsuite
```

The PyPI index contains only **release** versions. The development version of
the package can be obtained by installing it from the GitLab's Package Registry.
The Package Registry have to be specified as index url. Authentication via
[personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html)
with scope set to `api` must be used.


## Usage

For `common`:
```
import lbr_testsuite
```
All stuff from common module are available directly under the lbr_testsuite
package.


For `data_table`:
```
from lbr_testsuite import data_table
```
Provides tools for storing results and generating graphs not only for
throughput tests.


For `executable`:
```
from lbr_testsuite import executable
```
Executable module provides Tool, AsyncTool and Daemon convenient classes for
**local** or **remote** execution of various commands.


For `ipconfigurer`:
```
from lbr_testsuite import ipconfigurer
```
Ipconfigurer provides API for ip configuration using pyroute2 library.


For `packet_crafter`:
```
from lbr_testsuite import packet_crafter
```
Classes providing high-level packet crafting. Used for `trex` module.


For `spirent`:
```
from lbr_testsuite import spirent
```
Provides API for Spirent Test Center (STC).


For `trex`:
```
from lbr_testsuite import trex
```
Provides our custom API for Cisco TRex traffic generator.
Official API is provided by required package [lbr_trex_client](https://pypi.org/project/lbr-trex-client/).


For `vlan_config`:
```
from lbr_testsuite import vlan_config
```
Helper class for VLAN configuration management.


## Repository Maintainers

- Jan Sobol, Jan.Sobol@cesnet.cz
- Pavel Krobot, Pavel.Krobot@cesnet.cz
- Dominik Tran, Dominik.Tran@cesnet.cz


## License

This project is licensed under the BSD-3-Clause License - see the
[LICENSE](LICENSE) file for details.


## Acknowledgement

The software was partially developed within the scope of the Security Research
Programme of the Czech Republic 2015-2022 (BV III / 1 VS) granted by the Ministry
of the Interior of the Czech Republic under the project No. VI20192022137 --
Adaptive protection against DDoS attacks (AdaptDDoS).
