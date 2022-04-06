"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>

Copyright: (C) 2020 CESNET, z.s.p.o.

Spirent REST API wrapper class.
"""

import os


try:
    from stcrestclient.stcpythonrest import StcPythonRest
except ImportError:
    raise ImportError(
        "Unable to import 'stcrestclient'. Install latest using 'pip install -U stcrestclient'."
    )


class StcPythonREST(StcPythonRest):
    """Spirent REST API wrapper class to simulate the same interface as
    our previous Spirent API classes, e.g. StcPythonTCP, etc. It is based
    on the official Spirent REST API client for python. For details have
    a look at https://github.com/Spirent/py-stcrestclient/tree/master.
    """

    def __init__(self, host, port, **kwargs):
        os.environ["STC_REST_API"] = str(1)
        os.environ["STC_SERVER_ADDRESS"] = str(host)
        os.environ["STC_SERVER_PORT"] = str(port)
        super().__init__(**kwargs)
