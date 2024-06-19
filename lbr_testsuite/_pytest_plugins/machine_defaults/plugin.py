"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020-2023 CESNET

Machine defaults pytest plug-in. It reads a JSON file containing default
arguments for pytest for a list of specified machines. The plugin injects
a subset of these options to the pytest configuration according to the
current machine's hostname as these options would be set as the command
line arguments.
"""

import json
import logging
import pathlib
import socket
import urllib.error
import urllib.parse
import urllib.request

import pytest


global_logger = logging.getLogger(__name__)


DEFAULT_MACHINE_NAME = "DEFAULT"


def pytest_addoption(parser):
    """Standard pytest hook to handle command line or `pytest.ini`
    file options. It defines `--machines-path` command line option
    and a pair of `--[no-]machines-defaults` command line options.

    Parameters
    ----------
    parser : _pytest.config.argparsing.Parser
        Pytest parser object
    """

    parser.addoption(
        "--machines-path",
        type=str,
        default=None,
        help=(
            "Path to machines.json file containing default arguments "
            "for running pytest on all machines"
        ),
    )


def get_machine_name():
    """It returns this machine's name, i.e., the first part of
    its hostname (full domain name). For example, for machine's
    hostname 'dpdk-test.liberouter.org' it returns 'dpdk-test'.

    Returns
    -------
    str
        This machine's name
    """

    return socket.gethostname().split(".")[0]


def read_machines_file(url):
    """The function expects URL of the machines JSON file with the
    predefined structure, see above. It reads the file, decodes it
    and returns it as a Python dictionary. For example in the
    following form:

    .. code-block:: python

        machines = {
            "machine_name":
                ...
                "pytest_options": {
                    "single_option": "single_value",
                    "multi_option": ["value_A", "value_B"],
                    ...
                },
            },
            'dpdk-test2': {
                ...
                "pytest_options": {
                    "access_vlan": 25,
                    "wired_loopback": [
                        "tge3,0000:03:00.0",
                        "tge11,0000:04:00.0"
                    ],
                },
                ...
            },
            ...
        }

    Please note, that the function works only if the scheme is fully
    specified. If file:// scheme used, only absolute paths supported.

    For example:
        * http://abc.xyz/mno/machines.json
        * file:///home/jenkins/machines.json

    Parameters
    ----------
    url : str
        Machines JSON file URL

    Returns
    -------
    dict()
        Decoded machines JSON file
    """

    try:
        with urllib.request.urlopen(url, timeout=60) as request:
            machines_json = request.read().decode()
        machines = json.loads(machines_json)
    except (urllib.error.URLError, json.decoder.JSONDecodeError) as e:
        global_logger.warning(f"{e}, when reading '{url}'")
        machines = {}

    return machines


def convert_path_to_url(path, workdir="/"):
    """It converts a file path to an absolute URL-based format containing
    the file:// scheme. If the path is already in the URL format, it
    returns the path as it is.

    Parameters
    ----------
    path : str
        File path to be converted
    workdir : str or Path, optional
        Working directory for relative paths to be converted, if not
        specified the root of the filesystem, i.e., `/` is used.

    Returns
    -------
    str
        Path converted to the absolute URL-based format
    """

    # add file:// scheme if not set
    url = urllib.parse.urlparse(path)
    if not url.scheme:
        url = url._replace(scheme="file")

    # convert relative paths to absolute
    if url.scheme == "file":
        urlpath = url.path
        if url.netloc and urlpath[0] == "/":
            urlpath = str(pathlib.Path(workdir) / url.netloc) + urlpath
        if urlpath[0] != "/":
            urlpath = str(pathlib.Path(workdir) / urlpath)
        url = url._replace(path=urlpath, netloc="")

    return url.geturl()


def get_command_line_option_names(cmd_options):
    """Extract option name from command-line options.

    Additionaly, replace '-' with '_' to be equal with option name
    in machines JSON file.

    For example, from
        --trunk-vlans='31,32,33,34'
    extract only
        trunk_vlans

    Parameters
    ----------
    cmd_options : tuple(str)
        The command-line arguments as passed to pytest.main()

    Returns
    ----------
    tuple(str)
        Extracted option names.
    """

    option_names = []
    for cmd_option in cmd_options:
        option_name = cmd_option.split("=")[0]
        option_name = option_name.strip("-")
        option_name = option_name.replace("-", "_")
        option_names.append(option_name)

    return option_names


def inject_machine_option(config, option, value):
    """It injects machine option to the set of existing pytest options.
    If the option does not exist, the value is ignored and a warning is displayed.

    Parameters
    ----------
    config : _pytest.config.Config
        Pytest config object
    option : str
        Option name to be injected
    value : str, int or list
        Option value to be injected
    """

    if not hasattr(config.option, option):
        global_logger.warning(f"invalid option --{option} found for this machine in the file")
        return

    configured = config.getoption(option)
    islist = isinstance(configured, (list, tuple))

    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            global_logger.warning(f"no values found for option --{option} in the file")
            return

        if not islist:
            if len(value) > 1:
                global_logger.warning(
                    f"only the first value of --{option}='{value}' will be "
                    "applied, option is scalar"
                )
            value = value[0]

    global_logger.info(f"option --{option}='{value}' applied for this host")
    setattr(config.option, option, value)


def _get_default_options(machines):
    try:
        return machines[DEFAULT_MACHINE_NAME]["pytest_options"]
    except KeyError:
        return dict()


def machine_defaults_setup(config):
    """Setup machine defaults arguments for the tests.

    Parameters
    ----------
    config : _pytest.config.Config
        Pytest config object
    """

    if not config.getoption("machines_path"):
        return

    path = config.getoption("machines_path")
    url = convert_path_to_url(path, config.inipath.parent)

    machines = read_machines_file(url)
    machine_name = get_machine_name()
    machine_options = _get_default_options(machines)

    if machine_name not in machines:
        global_logger.warning(
            f"machine '{machine_name}' not found in machine defaults file '{path}'"
        )
    else:
        if "pytest_options" in machines[machine_name]:
            machine_options.update(machines[machine_name]["pytest_options"])
        else:
            global_logger.warning(
                f"pytest_options section not found in machine defaults file '{path}' for "
                f"'{machine_name}' machine"
            )

    cmd_option_names = get_command_line_option_names(config.invocation_params.args)

    for option, value in machine_options.items():
        if option in cmd_option_names:
            global_logger.warning(
                f"option --{option}='{value}' skipped due to value "
                f"'{config.getoption(option)}' already set via command-line"
            )
            continue

        inject_machine_option(config, option, value)


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """We register machine defaults functionality in pytest_sessionstart()
    hook rather that in pytest_configure() because at this time the looger
    is fully configured but not in pytest_configure(). The hookimpl
    decorator than ensures executing this hook as soon as possible to
    prevent any other plugin to access the config at this stage before
    machine defaults are set.

    Parameters
    ----------
    session : pytest.Session
        Pytest session object
    """

    machine_defaults_setup(session.config)
