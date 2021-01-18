# Python package lbr_testsuite

The purpose of this package is to provide common set of tools
that can be used in development of tests. Package now contains
`ipconfigurer` module and `TRex` tools.

## Hosting and contribution

Package `lbr_testsuite` is hosted in GitLab's Package Registry
under PyPI package manager. You can list all available versions
by following this [link](https://gitlab.liberouter.org/tmc/testsuite/-/packages).

This project uses GitLab CI pipeline which is triggered
with every new commit. If coding style (PEP8) check passes, then
pipeline creates .whl package from contents inside [lbr_testsuite](./lbr_testsuite)
folder. This package can be found in `build` step of pipeline and downloaded
for manual installation.

If pipeline triggers on `master` branch, then package is also uploaded into
Package Registry. If version of package(defined in [setup.py](./setup.py)) already
exists in Package Registry, then package is rejected.
This means that if you make **changes**, then you also need to **increase version**.


## Installation

You can click on some specific version of package from [list](https://gitlab.liberouter.org/tmc/testsuite/-/packages)
and GitLab will show you details of that package. This also
includes pip command for installation of package. Command looks like this:

```
pip install lbr-testsuite --extra-index-url https://__token__:<your_personal_token>@gitlab.liberouter.org/api/v4/projects/30/packages/pypi/simple
```

`lbr_testsuite` package is hosted on GitLab and isn't
included in official PyPI index, so you need to specify extra URL
for pip. And since this project is private, you need credentials
to access Package Registry. Preffered way is to use project's
**deploy token**. Then you can use this command for installation:

```
python3.6 -m pip install lbr-testsuite --extra-index-url https://gitlab+deploy-token-13:dPyQaA7ypwhNLxSttz2r@gitlab.liberouter.org/api/v4/projects/30/packages/pypi/simple
```

Another way is to use [personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) with
scope set to `api`.


## Usage

For `ipconfigurer`:
```
import lbr_testsuite.ipconfigurer as ipconf
```
Ipconfigurer provides API for ip configuration using pyroute2 library.


For `TRex` tools:
```
from lbr_testsuite.trex_tools.trex_instances import TRex_Instances
from lbr_testsuite.trex_tools.trex_stl_stream_generator import TRex_Stl_Stream_Generator
from lbr_testsuite.trex_tools.trex_astf_profile_generator import TRex_Astf_Profile_Generator
```
These tools provide some useful methods to work with TRex. They are
built on top of official API and make certain things much easier.
