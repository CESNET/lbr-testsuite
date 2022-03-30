"""
    Author(s): Jan Kucera <jan.kucera@cesnet.cz>, Pavel Krobot <Pavel.Krobot@cesnet.cz>
    Copyright: (C) 2019 CESNET

    Description: A custom implementation of SpirentTestCenter Python API using
    wrapped TCL API.
"""

import logging
import os
import pprint
import re
import sys
import time
from tkinter import Tcl


class StcPythonTcl:
    """
    This is a custom version of SpirentTestCenter Python API using wrapped TCL API.
    All public methods remain the same, including their input and output formats.
    Every deviation from the original StcPython is a bug.
    """

    def __init__(self):
        self._tcl = Tcl()
        self._load_library()

    def _load_library(self):
        command = "package require SpirentTestCenter"
        self._tcl.eval(command)

    def apply(self):
        return self._tcl.eval("stc::apply")

    def config(self, _object, **kwargs):
        svec = []
        StcPythonTcl._packKeyVal(svec, kwargs)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::config {} {}".format(_object, svec_string))

    def connect(self, *hosts):
        svec = StcPythonTcl._unpackArgs(*hosts)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::connect {}".format(svec_string))

    def create(self, _type, **kwargs):
        svec = []
        if _type.lower() != "project":
            svec.append("-under")
            svec.append(kwargs.pop("under"))

        StcPythonTcl._packKeyVal(svec, kwargs)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::create {} {}".format(_type, svec_string))

    def delete(self, handle):
        return self._tcl.eval("stc::delete {}".format(handle))

    def disconnect(self, *hosts):
        svec = StcPythonTcl._unpackArgs(*hosts)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::disconnect {}".format(svec_string))

    def get(self, handle, *args):
        svec = StcPythonTcl._unpackArgs(*args)
        svec_dashes = []

        for _, att_name in enumerate(svec):
            svec_dashes.append("-" + att_name)

        svec_string = " ".join(svec_dashes)
        tcl_output = self._tcl.eval("stc::get {} {}".format(handle, svec_string))
        # print('[StcPythonTcl DEBUG] Printing tcl get output:')
        # pprint.pprint(tcl_output)
        # print('-------------------------------------------------------------')
        # print(tcl_output)
        if len(tcl_output.split(" ")) == 1:
            print("<Single output>")
            return tcl_output
        else:
            parsed_output = StcPythonTcl._parse_tcl_output(tcl_output)
            # print('[StcPythonTcl DEBUG] Printing parsed output')
            # pprint.pprint(parsed_output)
            # print('-------------------------------------------------------------')
            # print(parsed_output)
            if type(parsed_output) == str:
                return parsed_output
            ret = StcPythonTcl._unpackGetResponseAndReturnKeyVal(parsed_output, svec)
            # print('[StcPythonTcl DEBUG] Printing unpacked value')
            # print(ret)
            return ret

    def help(self, topic=""):
        if topic == "" or topic.find(" ") != -1:
            return (
                "Usage: \n"
                + "  stc.help('commands')\n"
                + "  stc.help(<handle>)\n"
                + "  stc.help(<className>)\n"
                + "  stc.help(<subClassName>)"
            )

        if topic == "commands":
            allCommands = []
            for commandHelp in StcIntPythonHelp.HELP_INFO.values():
                allCommands.append(commandHelp["desc"])
            allCommands.sort()
            return "\n".join(allCommands)

        info = StcIntPythonHelp.HELP_INFO.get(topic)
        if info:
            return (
                "Desc: "
                + info["desc"]
                + "\n"
                + "Usage: "
                + info["usage"]
                + "\n"
                + "Example: "
                + info["example"]
                + "\n"
            )

    def log(self, level, msg):
        return self._tcl.eval("stc::log {} {}".format(level, msg))

    def perform(self, _cmd, **kwargs):
        svec = []
        StcPythonTcl._packKeyVal(svec, kwargs)
        svec_string = " ".join(svec)

        tcl_output = self._tcl.eval("stc::perform {} {}".format(_cmd, svec_string))
        # print('[StcPythonTcl DEBUG] Printing tcl get output:')
        # pprint.pprint(tcl_output)
        # print('-------------------------------------------------------------')
        # print(tcl_output)

        parsed_output = self._parse_tcl_output(tcl_output)
        # print('[StcPythonTcl DEBUG] Printing perform parsed output')
        # pprint.pprint(parsed_output)
        # print('-------------------------------------------------------------')
        # print(parsed_output)
        if type(parsed_output) == str:
            return parsed_output
        ret = StcPythonTcl._unpackPerformResponseAndReturnKeyVal(parsed_output, kwargs.keys())
        # print('[StcPythonTcl DEBUG] Printing unpacked value')
        # print(ret)
        return ret

    def release(self, *csps):
        svec = StcPythonTcl._unpackArgs(*csps)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::release {}".format(svec_string))

    def reserve(self, *csps):
        svec = StcPythonTcl._unpackArgs(*csps)
        svec_string = " ".join(svec)
        return self._tcl.eval("stc::reserve {}".format(svec_string))

    def sleep(self, seconds):
        time.sleep(seconds)

    def subscribe(self, **kwargs):
        svec = []
        StcPythonTcl._packKeyVal(svec, kwargs)
        svec_string = " ".join(svec)

        return self._tcl.eval("stc::subscribe {}".format(svec_string))

    def unsubscribe(self, rdsHandle):
        return self._tcl.eval("stc::unsubscribe {}".format(rdsHandle))

    def waitUntilComplete(self, **kwargs):
        timeout = 0
        if "timeout" in kwargs:
            timeout = int(kwargs["timeout"])

        sequencer = self.get("system1", "children-sequencer")

        timer = 0

        while True:
            curTestState = self.get(sequencer, "state")
            if "PAUSE" in curTestState or "IDLE" in curTestState:
                break

            time.sleep(1)
            timer += 1

            if timeout > 0 and timer > timeout:
                raise Exception("ERROR: Stc.waitUntilComplete timed out after " "%s sec" % timeout)

        if (
            "STC_SESSION_SYNCFILES_ON_SEQ_COMPLETE" in os.environ
            and os.environ["STC_SESSION_SYNCFILES_ON_SEQ_COMPLETE"] == "1"
            and self.perform("CSGetBllInfo")["ConnectionType"] == "SESSION"
        ):
            self.perform("CSSynchronizeFiles")

        return self.get(sequencer, "testState")

    @staticmethod
    def _parse_tcl_output(tcl_output: str):
        # REGEX explaied:
        # multiword strings | -key value | -key {v a l u e s}
        # regex = r"(\w+-?\w+ ?\w+-?\w+)|(-[^\s]+\s+[^\s|{]+)|(-[^\s]+)\s+{([\w|\s]*)}(-[^\s]+\s+[^\s|{]+)|(-[^\s]+)\s+{([\w|\s]*)}"

        regex = r"(^[\w\n\s:\\\/=,._';+<>~!?()\[\]@#$%^&*-]*$)|(-[^\s]+\s+[^\s|{]+)|(-[^\s]+)\s+{([\w\n\s:\\\/-=,._';+<>~!?()\[\]@#$%^&*]*)}"
        matches = re.finditer(regex, tcl_output, re.MULTILINE)
        parsed_output = []

        for match in matches:
            if match.group(1):
                return match.group(1)
            # Groups 3 and 4 match key and multi-value
            if match.group(2) is None:
                key = match.group(3)
                value = match.group(4)
            # Group 1 matches key and single-value pair
            else:
                key_val = match.group(2).split(" ")
                key = key_val[0]
                # This is a hack used to prevent XML string configuration from crashing
                value = ""
                if len(key_val) > 1:
                    value = key_val[1]

            parsed_output.append(key)
            parsed_output.append(value)

        return parsed_output

    @staticmethod
    def _packKeyVal(svec, hash):
        """Modified for empty value and multi-value"""
        for key, val in sorted(hash.items()):
            svec.append("-" + str(key))
            if isinstance(val, list):
                svec.append(" ".join(map(str, val)))
            else:
                if isinstance(val, bytes):
                    val = val.decode("ascii")
                if not val:
                    val = '""'
                elif len(str(val).split(" ")) > 1:
                    val = "{" + str(val) + "}"
                svec.append(str(val))

    @staticmethod
    def _unpackArgs(*args):
        svec = []
        for arg in args:
            if isinstance(arg, list):
                svec.extend(arg)
            else:
                svec.append(arg)
        return svec

    @staticmethod
    def _unpackGetResponseAndReturnKeyVal(svec, origKeys):
        useOrigKey = len(origKeys) == len(svec) / 2
        hash = dict()
        for i in range(0, int(len(svec) / 2)):
            key = svec[i * 2]
            key = key[1 : len(key)]
            val = svec[i * 2 + 1]
            if useOrigKey:
                key = origKeys[i]
            hash[key] = val
        return hash

    @staticmethod
    def _unpackPerformResponseAndReturnKeyVal(svec, origKeys):
        origKeyHash = dict()
        for key in origKeys:
            origKeyHash[key.lower()] = key

        hash = dict()
        for i in range(0, int(len(svec) / 2)):
            key = svec[i * 2]
            key = key[1 : len(key)]
            val = svec[i * 2 + 1]
            if key.lower() in origKeyHash:
                key = origKeyHash[key.lower()]
            hash[key] = val
        return hash


# internal help info
class StcIntPythonHelp(object):
    def __init__(self):
        pass

    HELP_INFO = dict(
        create=dict(
            desc="create: -Creates an object in a test hierarchy",
            usage="stc.create( className, under = parentObjectHandle, propertyName1 = propertyValue1, ... )",
            example="stc.create( 'port', under='project1', location = \"#{mychassis1}/1/2\" )",
        ),
        config=dict(
            desc="config: -Sets or modifies the value of an attribute",
            usage="stc.config( objectHandle, propertyName1 = propertyValue1, ... )",
            example="stc.config( stream1, enabled = true )",
        ),
        get=dict(
            desc="get: -Retrieves the value of an attribute",
            usage="stc.get( objectHandle, propertyName1, propertyName2, ... )",
            example="stc.get( stream1, 'enabled', 'name' )",
        ),
        perform=dict(
            desc="perform: -Invokes an operation",
            usage="stc.perform( commandName, propertyName1 = propertyValue1, ... )",
            example="stc.perform( 'createdevice', parentHandleList = 'project1' createCount = 4 )",
        ),
        delete=dict(
            desc="delete: -Deletes an object in a test hierarchy",
            usage="stc.delete( objectHandle )",
            example="stc.delete( stream1 )",
        ),
        connect=dict(
            desc="connect: -Establishes a connection with a Spirent TestCenter chassis",
            usage="stc.connect( hostnameOrIPaddress, ... )",
            example="stc.connect( mychassis1 )",
        ),
        disconnect=dict(
            desc="disconnect: -Removes a connection with a Spirent TestCenter chassis",
            usage="stc.disconnect( hostnameOrIPaddress, ... )",
            example="stc.disconnect( mychassis1 )",
        ),
        reserve=dict(
            desc="reserve: -Reserves a port group",
            usage="stc.reserve( CSP1, CSP2, ... )",
            example='stc.reserve( "//#{mychassis1}/1/1", "//#{mychassis1}/1/2" )',
        ),
        release=dict(
            desc="release: -Releases a port group",
            usage="stc.release( CSP1, CSP2, ... )",
            example='stc.release( "//#{mychassis1}/1/1", "//#{mychassis1}/1/2" )',
        ),
        apply=dict(
            desc="apply: -Applies a test configuration to the Spirent TestCenter firmware",
            usage="stc.apply()",
            example="stc.apply()",
        ),
        log=dict(
            desc="log: -Writes a diagnostic message to the log file",
            usage="stc.log( logLevel, message )",
            example="stc.log( 'DEBUG', 'This is a debug message' )",
        ),
        waitUntilComplete=dict(
            desc="waitUntilComplete: -Suspends your application until the test has finished",
            usage="stc.waitUntilComplete()",
            example="stc.waitUntilComplete()",
        ),
        subscribe=dict(
            desc="subscribe: -Directs result output to a file or to standard output",
            usage="stc.subscribe( parent=parentHandle, resultParent=parentHandles, configType=configType, resultType=resultType, viewAttributeList=attributeList, interval=interval, fileNamePrefix=fileNamePrefix )",
            example="stc.subscribe( parent='project1', configType='Analyzer', resulttype='AnalyzerPortResults', filenameprefix='analyzer_port_counter' )",
        ),
        unsubscribe=dict(
            desc="unsubscribe: -Removes a subscription",
            usage="stc.unsubscribe( resultDataSetHandle )",
            example="stc.unsubscribe( resultDataSet1 )",
        ),
    )
