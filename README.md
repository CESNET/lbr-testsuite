# Python package lbr_testsuite

The purpose of this package is to provide common set of tools
that can be used in development of tests. Package now contains
`common`, `ipconfigurer`, `executable`, `spirent`, `spirentlib` modules and
`TRex` tools.

## Hosting and contribution

Package `lbr_testsuite` is hosted in GitLab's Package Registry
under PyPI package manager. You can list all available versions
by following this [link](https://gitlab.liberouter.org/tmc/pypi-liberouter/-/packages).

This project uses GitLab CI pipeline which is triggered
with every new commit. If coding style (PEP8) check passes, then
pipeline creates .whl package from contents inside [lbr_testsuite](./lbr_testsuite)
folder. This package can be found in `build` step of pipeline and downloaded
for manual installation.

If pipeline triggers on `master` branch, then package is also uploaded into
the Package Registry. Version of the package is controlled using git tags.
Package names are composed from current version and hash of last commit.


## Installation

You can click on some specific version of package from [list](https://gitlab.liberouter.org/tmc/pypi-liberouter/-/packages)
and GitLab will show you details of that package. This also
includes pip command for installation of package. Command looks like this:

```
pip install lbr-testsuite --extra-index-url https://__token__:<your_personal_token>@gitlab.liberouter.org/api/v4/projects/95/packages/pypi/simple
```

`lbr_testsuite` package is hosted on GitLab and isn't
included in official PyPI index, so you need to specify extra URL
for pip. And since this project is private, you need credentials
to access Package Registry. This project uses **deploy token**, but
you can also use [personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) with
scope set to `api`.


For installation of `lbr_testsuite` you can use one of these commands:

```
python3.8 -m pip install lbr-testsuite --extra-index-url https://gitlab+deploy-token-13:dPyQaA7ypwhNLxSttz2r@gitlab.liberouter.org/api/v4/projects/95/packages/pypi/simple
*or*
python3.8 -m pip install lbr-testsuite --extra-index-url http://cisticka-devel.liberouter.org/piproxy/tmc/pypi-liberouter/simple --trusted-host cisticka-devel.liberouter.org
```

## Usage

For `common`:
```
import lbr_testsuite
```
All stuff from common module are available directly under the lbr_testsuite
package.

For `ipconfigurer`:
```
from lbr_testsuite import ipconfigurer
```
Ipconfigurer provides API for ip configuration using pyroute2 library.


For `executable`:
```
from lbr_testsuite import executable
```
Executable module provides Tool and Daemon convenient classes for execution of
various commands.


For `spirent` and `spirentlib`:
```
from lbr_testsuite import spirent
from lbr_testsuite.spirent import spirentlib
```
Provides API for Spirent Test Center (STC).


For `TRex` tools:
```
from lbr_testsuite.trex_tools.trex_instances import TRex_Instances
from lbr_testsuite.trex_tools.trex_stl_stream_generator import TRex_Stl_Stream_Generator
from lbr_testsuite.trex_tools.trex_astf_profile_generator import TRex_Astf_Profile_Generator
```
These tools provide some useful methods to work with TRex. They are
built on top of official API and make certain things much easier.


## Repository Maintainer

- Pavel Krobot, Pavel.Krobot@cesnet.cz


## Acknowledgement

The software was partially developed within the scope of the Security Research
Programme of the Czech Republic 2015-2022 (BV III / 1 VS) granted by the Ministry
of the Interior of the Czech Republic under the project No. VI20192022137 --
Adaptive protection against DDoS attacks (AdaptDDoS).
