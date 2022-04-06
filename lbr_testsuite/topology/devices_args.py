"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2022 CESNET

Class representation of devices arguments.
"""


class DevicesArgs:
    """Representation of devices arguments.

    Attributes
    ----------
    _args : dict[dict[str]]
        Devices arguments represented as a dictionary that
        maps device name to a dictionary of its arguments.
    """

    def __init__(self, options):
        """Devices arguments object.

        Parameters
        ----------
        options : list[str]
            List of device arguments in comma separared form
            <device-name>[,<arg1>=<value1>[,<arg2>=<value2>...]]
        """

        self._args = {}

        for option in options:
            device_name, args = option.split(",", 1)

            device_args = {}
            for arg in args.split(","):
                key, value = arg.split("=")
                device_args[key] = value

            self._args[device_name] = device_args

    def __getitem__(self, device_name):
        """Returns arguments for the device specified by `device_name`.

        Parameters
        ----------
        device_name : str
            List of key=value pairs or comma separated pairs.

        Returns
        -------
        dict[str]
            Dictionary of device arguments.
        """

        return self._args.get(device_name, [])
