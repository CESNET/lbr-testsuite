"""
Author(s): Jan Kucera <jan.kucera@cesnet.cz>, Pavel Krobot <Pavel.Krobot@cesnet.cz>
Copyright: (C) 2019 CESNET, z.s.p.o.
"""

import logging
import re

from .stcapi.StcPythonREST import StcPythonREST
from .stcapi.StcPythonTCP import StcPythonTCP


global_logger = logging.getLogger(__name__)


STC_API_PROPRIETARY = 0
STC_API_OFFICIAL = 1


class StcHandler:
    """Basic STC configuration class"""

    def __init__(self, stc_api_version=STC_API_OFFICIAL, stc_api_session_start_timeout=120):
        self._stc_api_version = stc_api_version
        self._stc_api_session_start_timeout = stc_api_session_start_timeout
        self._stc = None
        self._generator_port_results = None
        self._analyzer_port_results = None
        self._filtered_stream_results = None
        self._rx_stream_block_results = None
        self._tx_stream_block_results = None
        self._overflow_results = None
        self._rx_port_pair_results = None
        self._tx_port_pair_results = None
        self._arpnd_results = None
        self._latency_results = None

    def stc_api_connect(self, host: str, port: int):
        if self._stc_api_version == STC_API_OFFICIAL:
            self._stc = StcPythonREST(
                host, port, session_start_timeout=self._stc_api_session_start_timeout
            )
        else:
            self._stc = StcPythonTCP(host, port)

    def stc(self):
        return self._stc

    def stc_init(self, xml_config_file: str):
        self.logging_config()
        self.load_xml(xml_config_file)
        self.set_sequencer()
        self.subscribe_to_results()

        # Always delete streams from analyzers
        xpath = self.stc_object_xpath("StcSystem/Project/ResultOptions")
        self.stc_attribute(xpath, "DeleteAllAnalyzerStreams", "TRUE")

        # Apply config
        self._stc.apply()

    def logging_config(self, level="error", file="stdout"):
        """
        Possible logLevel values are: DEBUG, INFO, WARN, and ERROR
        Possible values for logTo are "stdout" or a file name (can include
        the path). Use forward slashes between directory names.
        """
        self._stc.config("automationoptions", logLevel=level, logTo=file)

    def load_xml(self, xml_config_file: str):
        """Load XML config using string format"""
        if self._stc_api_version == STC_API_OFFICIAL:
            return self._stc.perform("loadfromxml", FileName=xml_config_file)
        else:
            with open(xml_config_file, "rb") as file:
                config_string = file.read()
            return self._stc.perform("loadfromxml", FileName="", InputConfigString=config_string)

    def set_sequencer(self):
        sequencer = self._stc.get("system1", "children-sequencer")
        self._stc.config(sequencer, errorHandler="stop_on_error")

    def stc_get_stream_block_load(self, sb_name):
        xpath = ["StcSystem/Project/Port/StreamBlock[@Name={}]".format(sb_name)]
        sb_handler = self.stc_object_xpath(xpath)

        load_handler = self.stc_get_attributes(sb_handler, "AffiliationStreamBlockLoadProfile")
        return self.stc_attribute(load_handler, "Load")

    def subscribe_to_results(self):
        project = self._stc.get("system1", "children-Project")

        # Port Traffic -> Basic Traffic Results
        self._generator_port_results = self.sub_generator_port_results(project)
        self._analyzer_port_results = self.sub_analyzer_port_results(project)
        # Stream Results -> Filtered Stream Results
        self._filtered_stream_results = self.sub_filtered_stream_results(project)
        # Stream Resilts -> Stream Block Results
        self._rx_stream_block_results = self.sub_rx_stream_block_results(project)
        self._tx_stream_block_results = self.sub_tx_stream_block_results(project)
        # Port Traffic -> Overflow Results
        self._overflow_results = self.sub_overflow_results(project)
        # Port Traffic -> Port Pair Results
        # Note: Requires RefreshResultView command (stc_refresh_results)
        self._rx_port_pair_results = self.sub_rx_port_pair_results(project)
        self._tx_port_pair_results = self.sub_tx_port_pair_results(project)
        # # Port Protocols -> ARPND Results
        self._arpnd_results = self.sub_arpnd_results(project)
        # Port -> Latency Results
        self._latency_results = self.sub_latency_results(project)

    def sub_generator_port_results(self, parent: str):
        generator_port_results = self._stc.subscribe(
            parent=parent,
            resultParent=parent,
            configType="generator",
            resultType="generatorportresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return generator_port_results

    def sub_analyzer_port_results(self, parent: str):
        analyzer_port_results = self._stc.subscribe(
            parent=parent,
            configType="analyzer",
            resultType="analyzerportresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return analyzer_port_results

    def sub_filtered_stream_results(self, parent: str):
        port = self._stc.get("system1.Project(1)", "children-Port")
        filtered_stream_results = self._stc.subscribe(
            parent=parent,
            resultParent=port,
            configType="analyzer",
            resultType="filteredstreamresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return filtered_stream_results

    def sub_rx_stream_block_results(self, parent: str):
        rx_stream_block_results = self._stc.subscribe(
            parent=parent,
            resultParent=parent,
            configType="streamblock",
            resultType="rxstreamblockresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return rx_stream_block_results

    def sub_tx_stream_block_results(self, parent: str):
        tx_stream_block_results = self._stc.subscribe(
            parent=parent,
            resultParent=parent,
            configType="streamblock",
            resultType="txstreamblockresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            viewAttributeList="framecount framerate bitrate",
            interval=1,
        )
        return tx_stream_block_results

    def sub_overflow_results(self, parent: str):
        port = self._stc.get("system1.Project(1)", "children-Port")
        overflow_results = self._stc.subscribe(
            parent=parent,
            resultParent=port,
            configType="analyzer",
            resultType="OverflowResults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return overflow_results

    def sub_tx_port_pair_results(self, parent: str):
        port = self._stc.get("system1.Project(1)", "children-Port")
        tx_port_pair_results = self._stc.subscribe(
            parent=parent,
            resultParent=port,
            configType="port",
            resultType="TxPortPairResults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return tx_port_pair_results

    def sub_rx_port_pair_results(self, parent: str):
        port = self._stc.get("system1.Project(1)", "children-Port")
        rx_port_pair_results = self._stc.subscribe(
            parent=parent,
            resultParent=port,
            configType="port",
            resultType="RxPortPairResults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return rx_port_pair_results

    def sub_arpnd_results(self, parent: str):
        port = self._stc.get("system1.Project(1)", "children-Port")
        arpnd_results = self._stc.subscribe(
            parent=parent,
            resultParent=port,
            configType="port",
            resultType="ArpNdResults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            interval=1,
        )
        return arpnd_results

    def sub_latency_results(self, parent: str):
        latency_results = self._stc.subscribe(
            parent=parent,
            resultParent=parent,
            configType="analyzer",
            resultType="portavglatencyresults",
            filterList="",
            disablePaging="true",
            recordsPerPage=256,
            viewAttributeList="avglatency maxlatency minlatency",
            interval=1,
        )
        return latency_results

    def stc_object_xpath(self, xpaths):
        # TODO: split this function to pieces so it's actually readable...
        # Handle single xpath as a list with 1 member
        if type(xpaths) == str:
            xpaths = xpaths.split()
        # Prepapre object handle list
        handles = []

        for xpath in xpaths:
            # print('Processing xpath: {}'.format(xpath))
            heap = []
            elements = xpath.split("/")

            for element in elements:
                # print('Processing element: {}'.format(element))
                # Split parts of the element term
                parts = re.findall(r"[^\[\]]+", element)
                # Extract name of the element
                name = parts.pop(0)
                # Find children
                if len(heap) == 0:
                    # print('Heap_len is 0: getting object {}'.format(name))
                    result = self._stc.perform("GetObjects", classname=name)
                    object_list = result["ObjectList"]
                    # print('Printing object list')
                    # pprint.pprint(object_list)
                    # Handle string result as a list with 1 member
                    if type(object_list) == list:
                        childheap = object_list
                    else:
                        childheap = object_list.split()
                else:
                    # print('Processing items in heap ...')
                    childheap = []
                    for item in heap:
                        # print("stc_get item '{}' children-{}".format(item, name))
                        child = self._stc.get(item, "children-" + name)
                        # print('Got children: ')
                        # pprint.pprint(child)
                        if len(child.split()) == 1:
                            childheap.append(child)
                        else:
                            childheap.extend(child.split())
                # Set new population
                heap = []
                # Iterate over children
                for child in childheap:
                    # print("Processing child in childheap")
                    # pprint.pprint(child)
                    filter = False
                    # Iterate over conditions
                    for part in parts:
                        # print("Processing part '{}'".format(part))
                        # Split condition
                        condition = part.split("=")
                        left_val = condition[0]
                        right_val = condition[1]

                        # Attribute value condition
                        if left_val[0] == "@":
                            # Wildcard test
                            if right_val == "*":
                                continue
                            attribute = left_val[1:]
                            # print('[wildcard test] Getting child')
                            # pprint.pprint(child)
                            # pprint.pprint(attribute)
                            value = self._stc.get(child, attribute)
                            # Compare attribute values
                            # print('right_val:')
                            # pprint.pprint(right_val)
                            # print('value:')
                            # pprint.pprint(value)
                            if right_val != value:
                                filter = True
                                break

                    # Optionally filter child
                    if not filter:
                        heap.append(child)
                # No nodes found: exit
                if len(heap) == 0:
                    break

            # Add heap to the list of handles
            handles.append(heap)
        # print('[object_xpath] Returning handles:')
        # pprint.pprint(handles)
        # print('--------------')
        return handles

    def stc_attribute(self, handles, attributes, values="", call_apply=True):
        if values == "":
            return self.stc_get_attributes(handles, attributes)
        else:
            self.stc_set_attributes(handles, attributes, values, call_apply)

    def stc_get_attributes(self, handles, attributes):
        # Handle single xpath as a list with 1 member
        if type(handles) == str:
            handles = handles.split()
        if type(attributes) == str:
            attributes = attributes.split()

        results = []
        name = attributes[0]

        for i, handle in enumerate(handles):
            values = []
            if len(attributes) > 1:
                name = attributes[i]
            for subhandle in handle:
                if name == "*":
                    values.append(self._stc.get(subhandle))
                else:
                    values.append(self._stc.get(subhandle, name))

            results.append(values)

        return results

    def stc_set_attributes(self, handles, attributes, values, call_apply=True):
        # Handle single xpath as a list with 1 member
        if type(handles) == str:
            handles = handles.split()
        if type(attributes) == str:
            attributes = attributes.split()
        if type(values) == str:
            values = values.split()

        name = attributes[0]
        value = values[0]

        for i, handle in enumerate(handles):
            if len(attributes) > 1:
                name = attributes[i]
            if len(values) > 1:
                value = values[i]
            for subhandle in handle:
                self._stc.config(subhandle, **{name: value})

        if call_apply:
            # Apply config
            self._stc.apply()

    def stc_delete(self, handles, call_apply=True):
        if type(handles) == str:
            handles = handles.split()

        for handle in handles:
            for subhandle in handle:
                self._stc.delete(subhandle)

        if call_apply:
            self._stc.apply()

    def stc_attribute_xpath(self, xpaths, values=""):
        # Handle single xpath as a list with 1 member
        if type(xpaths) == str:
            xpaths = xpaths.split()

        attributes = []
        object_xpaths = []

        for xpath in xpaths:
            object_xpath, attribute = xpath.rsplit("/", 1)
            object_xpaths.append(object_xpath)
            attributes.append(attribute)

        # Get object handles
        handles = self.stc_object_xpath(object_xpaths)

        # Get/Set values
        return self.stc_attribute(handles, attributes, values)

    def stc_connect(self, host: str, ports: str, force_ports=False):
        port_list = ports.split(" ")

        if len(port_list) == 0:
            return

        stc_port_objects = self._stc.perform(
            "getObjects", classname="Port", condition="isVirtual=false"
        )
        stc_port_object_list = stc_port_objects["ObjectList"]
        stc_port_object_list = stc_port_object_list.split(" ")

        for stc_port in stc_port_object_list:
            # Set proper //host/slot/port format
            location_string = "//{}/{}".format(host, port_list.pop(0))
            self._stc.config(stc_port, location=location_string)
            self._stc.config(stc_port, name=location_string)

        # Apply settings
        self._stc.apply()

        # Perform the logical to physical port mapping, connect to the chassis and reserve the ports
        project_ports = self._stc.get("project1", "children-Port")
        self._stc.perform(
            "attachPorts",
            autoconnect="true",
            portlist=project_ports,
            revokeowner=str(force_ports).lower(),
        )

    def stc_disconnect(self):
        self._stc.perform("chassisDisconnectAll")
        self._stc.perform("resetConfig")

    @staticmethod
    def _assert_supported_result_view_mode(mode):
        assert mode in [
            "BASIC",
            "HISTOGRAM",
            "JITTER",
            "INTERARRIVALTIME",
            "FORWARDING",
            "LATENCY_JITTER",
        ], f"Unsupported mode '{mode}'"

    def _result_options_handler(self):
        xpath = ["StcSystem/Project/ResultOptions"]
        return self.stc_object_xpath(xpath)

    def stc_set_result_view_mode(self, mode):
        self._assert_supported_result_view_mode(mode)
        self.stc_attribute(self._result_options_handler(), "ResultViewMode", mode)

    def stc_check_result_view_mode(self, mode):
        self._assert_supported_result_view_mode(mode)
        current_mode = self.stc_attribute(self._result_options_handler(), "ResultViewMode")[0][0]
        return current_mode == mode

    def stc_start_arpnd(self):
        project_ports = self._stc.get("project1", "children-Port")
        self._stc.perform("ArpNdStartCommand", handleList=project_ports)

    def stc_start_generators(self, timeout=10):
        # Set logging
        self.logging_config()

        all_stream_blocks = self.stc_stream_block()
        if "true" not in self.stc_attribute(all_stream_blocks, "Active")[0]:
            global_logger.warning("There are no active stream-block. No traffic will be generated.")

        # Get all generator handles
        generator_objects = self._stc.perform("getObjects", classname="Generator")
        generators = generator_objects["ObjectList"].split(" ")

        # Get continuous generators handles only
        continuous_generators = []
        for generator in generators:
            gen_duration_mode = self._stc.get(
                "{}.generatorConfig".format(generator), "durationMode"
            )
            if gen_duration_mode == "CONTINUOUS":
                continuous_generators.append(generator)

        # Start generators and wait 1 second
        self._stc.perform("generatorStart", generatorList=generators)
        if len(continuous_generators) != 0:
            res = self._stc.perform(
                "generatorWaitForStart",
                generatorList=continuous_generators,
                waittimeout=timeout,
            )
            if res["Status"]:
                # If there is an error, the status will show what failed. Otherwise it is empty.
                raise RuntimeError(
                    f"Generator(s) did not start after {timeout} seconds. "
                    f"Error message from STC: {res['Status']}"
                )

        self._stc.perform("wait", waitTime=1)

    def stc_stop_generators(self):
        # Get all generator handles
        generator_objects = self._stc.perform("getObjects", classname="Generator")
        generators = generator_objects["ObjectList"].split(" ")

        # Get continuous generators handles only
        continuous_generators = []
        for generator in generators:
            gen_duration_mode = self._stc.get(
                "{}.generatorConfig".format(generator), "durationMode"
            )
            if gen_duration_mode == "CONTINUOUS":
                continuous_generators.append(generator)

        # Stop generators and wait 1 second
        if len(continuous_generators) != 0:
            self._stc.perform("generatorStop", generatorList=continuous_generators)
        self._stc.perform("generatorWaitForStop", generatorList=generators)
        self._stc.perform("wait", waitTime=1)

    def stc_start_analyzers(self):
        # Get all analyzer handles
        analyzer_objects = self._stc.perform("getObjects", className="Analyzer")
        analyzers = analyzer_objects["ObjectList"].split(" ")

        # Start analyzers and wait 1 second
        self._stc.perform("analyzerStart", analyzerList=analyzers)
        self._stc.perform("wait", waitTime=1)

    def stc_stop_analyzers(self):
        # Get all analyzer handles
        analyzer_objects = self._stc.perform("getObjects", className="Analyzer")
        analyzers = analyzer_objects["ObjectList"].split(" ")

        # Stop analyzers and wait 1 second
        self._stc.perform("analyzerStop", analyzerList=analyzers)
        self._stc.perform("wait", waitTime=1)

    def stc_refresh_results(self):
        self._stc.perform("RefreshResultView", resultDataSet=self._rx_stream_block_results)
        self._stc.perform("RefreshResultView", resultDataSet=self._tx_stream_block_results)
        self._stc.perform("RefreshResultView", resultDataSet=self._latency_results)

    def stc_clear_results(self):
        ports = self._stc.get("project1", "children-Port")
        self._stc.perform("ResultsClearAll", portList=ports)

    def stc_stream_block(self, names="*"):
        # HACK: This line handles strange behavior of STC API where
        # stream block is not accessible before its parent is accessed.
        self._stc.get(self.stc_object_xpath("StcSystem/Project/Port")[0][0])

        # Handle default input
        if type(names) == str:
            names = [x for x in names.split()]

        xpaths = []

        for name in names:
            xpaths.append("StcSystem/Project/Port/StreamBlock[@Name={}]".format(name))

        return self.stc_object_xpath(xpaths)

    def stc_device(self, names="*"):
        # Handle default input
        if type(names) == str:
            names = [x for x in names.split()]

        xpaths = []

        for name in names:
            xpaths.append("StcSystem/Project/EmulatedDevice[@Name={}]".format(name))

        return self.stc_object_xpath(xpaths)

    def stc_get_stream_block_load_unit(self, sb_name):
        xpath = ["StcSystem/Project/Port/StreamBlock[@Name={}]".format(sb_name)]
        sb_handler = self.stc_object_xpath(xpath)

        load_handler = self.stc_get_attributes(sb_handler, "AffiliationStreamBlockLoadProfile")
        return self.stc_attribute(load_handler, "LoadUnit")[0][0]

    def stc_get_line_speed_mbps(self):
        _LINE_SPEEDS_TABLE = dict(
            SPEED_UNKNOWN=0,
            SPEED_10M=10,
            SPEED_100M=100,
            SPEED_1G=1000,
            SPEED_2500M=2500,
            SPEED_5G=5000,
            SPEED_10G=10_000,
            SPEED_25G=25_000,
            SPEED_40G=40_000,
            SPEED_50G=50_000,
            SPEED_100G=100_000,
            SPEED_200G=200_000,
            SPEED_400G=400_000,
        )
        xpath = ["StcSystem/Project/Port"]
        port_handler = self.stc_object_xpath(xpath)
        phy_handler = self.stc_get_attributes(port_handler, "ActivePhy")
        line_speed = self.stc_attribute(phy_handler, "LineSpeed")[0][0]
        return _LINE_SPEEDS_TABLE[line_speed]

    def stc_set_port_scheduling_mode(self, mode):
        """Set port scheduling mode.

        The scheduling mode affects the sequence in which frames from
        each stream block are transmitted.

        Parameters
        ----------
        mode : str
            Scheduling mode. Allowed modes are 'port', 'rate',
            'priority' and 'manual'.

        Raises
        ------
        ValueError
            If invalid mode passed.
        """

        xpath = ["StcSystem/Project/Port/Generator/GeneratorConfig"]
        gen_config_handler = self.stc_object_xpath(xpath)

        if mode == "port":
            self.stc_attribute(gen_config_handler, "SchedulingMode", "PORT_BASED")
        elif mode == "rate":
            self.stc_attribute(gen_config_handler, "SchedulingMode", "RATE_BASED")
        elif mode == "priority":
            self.stc_attribute(gen_config_handler, "SchedulingMode", "PRIORITY_BASED")
        elif mode == "manual":
            self.stc_attribute(gen_config_handler, "SchedulingMode", "MANUAL_BASED")
        else:
            raise ValueError(
                "Invalid scheduling mode '{mode}'. Allowed scheduling modes are "
                "'port', 'rate', 'priority' and 'manual'."
            )

    def stc_set_port_load(self, port_load_type, port_load_value):
        """Set port load.

        Method allows caller to set fixed port load for port based
        scheduling mode. Allowed port load types are percentage, frames
        per second or bits per second.

        Parameters
        ----------
        port_load_type : str
            Selected port load type, one of 'perc' (for percentage),
            'fps' (for frames per second) or 'bps' bits per second.
        port_load_value : int
            Port load value (has to correspond with selected type).

        Raises
        ------
        RuntimeError
            If method is called on STC configuration with scheduling
            mode different than port based.
        ValueError
            If invalid port load type is used in argument.
        """

        # Check whether port load in STC configuration is set to port-based
        xpath = ["StcSystem/Project/Port/Generator/GeneratorConfig"]
        gen_config_handler = self.stc_object_xpath(xpath)

        scheduling_mode = self.stc_attribute(gen_config_handler, "SchedulingMode")[0][0]
        if scheduling_mode != "PORT_BASED":
            raise RuntimeError(
                "Invalid port load mode in the STC configuration. Port-based mode is requested."
            )

        # Set port load unit according to requested port load type
        if port_load_type == "perc":
            self.stc_attribute(
                gen_config_handler, "LoadUnit", "PERCENT_LINE_RATE", call_apply=False
            )
        elif port_load_type == "fps":
            self.stc_attribute(
                gen_config_handler, "LoadUnit", "FRAMES_PER_SECOND", call_apply=False
            )
        elif port_load_type == "bps":
            self.stc_attribute(gen_config_handler, "LoadUnit", "BITS_PER_SECOND", call_apply=False)
        else:
            raise ValueError(
                "Invalid port load type argument '{}'. Allowed port load types "
                "are 'perc', 'fps' or 'bps'.".format(port_load_type)
            )

        # Set port load mode to fixed
        self.stc_attribute(gen_config_handler, "LoadMode", "FIXED", call_apply=False)
        # Set port load value
        self.stc_attribute(gen_config_handler, "FixedLoad", str(port_load_value), call_apply=False)

        self._stc.apply()

    def stc_set_stream_block_load(self, sb_name, sb_load):
        xpath = ["StcSystem/Project/Port/StreamBlock[@Name={}]".format(sb_name)]
        sb_handler = self.stc_object_xpath(xpath)

        load_handler = self.stc_get_attributes(sb_handler, "AffiliationStreamBlockLoadProfile")
        self.stc_attribute(load_handler, "Load", sb_load)

    def stc_set_stream_block_packet_length(self, sb_name, pkt_len):
        xpath = ["StcSystem/Project/Port/StreamBlock[@Name={}]/FixedFrameLength".format(sb_name)]
        self.stc_attribute_xpath(xpath, str(pkt_len))

    def stc_set_traffic_gen_seconds(self, duration):
        """Set traffic generation duration in seconds.

        Method sets duration mode of traffic generation to "Seconds" and
        sets requested seconds as duration.

        Parameters
        ----------
        duration : int
            Traffic generation duration in seconds.
        """

        # Check whether port load in STC configuration is set to port-based
        xpath = ["StcSystem/Project/Port/Generator/GeneratorConfig"]
        gen_config_handler = self.stc_object_xpath(xpath)

        # Set duration mode to "seconds"
        self.stc_attribute(gen_config_handler, "DurationMode", "SECONDS", call_apply=False)
        # Set duration length
        self.stc_attribute(gen_config_handler, "Duration", str(duration), call_apply=False)

        self._stc.apply()

    def stc_start_stream_block(self, stream_block):
        sb_list = self.stc_stream_block(stream_block)[0]
        self._stc.perform("StreamBlockStart", streamblocklist=sb_list)

    def stc_stop_stream_block(self, stream_block):
        sb_list = self.stc_stream_block(stream_block)[0]
        self._stc.perform("StreamBlockStop", streamblocklist=sb_list)

    def stc_tx_stream_block_results(self, stream_blocks, names="*"):
        result_handles = self.stc_attribute(stream_blocks, "children-TxStreamBlockResults")
        return self.stc_attribute(result_handles, names)

    def stc_rx_stream_block_results(self, stream_blocks, names="*"):
        result_handles = self.stc_attribute(stream_blocks, "children-RxStreamBlockResults")
        return self.stc_attribute(result_handles, names)

    def stc_filtered_stream_results(self, names="*", sb_name=None):
        if type(names) == str:
            names = [x for x in names.split()]
        results = []
        total_page_count = self.stc_attribute([[self._filtered_stream_results]], "TotalPageCount")

        stream_id = None
        if sb_name:
            """
            Matching stream blocks with stream IDs in this way will only work
            when stream blocks containing only single streams are used.
            """
            sb = self.stc_stream_block(sb_name)
            stream_id = int(self.stc_get_attributes(sb, "StreamBlockIndex")[0][0])

        for page in range(1, int(total_page_count[0][0]) + 1):
            # Set page
            self.stc_attribute([[self._filtered_stream_results]], "PageNumber", str(page))
            # Find specific object
            objects = self._stc.perform("getObjects", className="FilteredStreamResults")
            filtered_stream_results = objects["ObjectList"].split(" ")
            if stream_id is None:
                handles = filtered_stream_results
            else:
                handles = [filtered_stream_results[stream_id]]
            results.append(self.stc_attribute([handles], names))

        return results

    def stc_analyzer_filter(self, values=""):
        objects = self._stc.perform("getObjects", className="AnalyzerFrameConfigFilter")
        analyzer_frame_config_filters = objects["ObjectList"].split(" ")

        # Get or set
        if values == "":
            return self.stc_attribute([analyzer_frame_config_filters], "FrameConfig")
        else:
            return self.stc_attribute([analyzer_frame_config_filters], "FrameConfig", values)

    def stc_generator_port_results(self, name: str):
        results = []

        # Get specific generator object
        generator_objects = self._stc.perform("getObjects", className="GeneratorPortResults")
        generator_port_results = generator_objects["ObjectList"].split(" ")

        for result in generator_port_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_analyzer_port_results(self, name: str):
        results = []

        # Get specific analyzer object
        analyzer_objects = self._stc.perform("getObjects", className="AnalyzerPortResults")
        analyzer_port_results = analyzer_objects["ObjectList"].split(" ")

        for result in analyzer_port_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_overflow_results(self, name: str):
        results = []

        # Get specific analyzer object
        overflow_objects = self._stc.perform("getObjects", className="OverflowResults")
        overflow_results = overflow_objects["ObjectList"].split(" ")

        for result in overflow_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_tx_port_pair_results(self, name: str):
        results = []

        # Get specific analyzer object
        txpp_objects = self._stc.perform("getObjects", className="TxPortPairResults")
        txpp_results = txpp_objects["ObjectList"].split(" ")

        for result in txpp_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_rx_port_pair_results(self, name: str):
        results = []

        # Get specific analyzer object
        rxpp_objects = self._stc.perform("getObjects", className="RxPortPairResults")
        rxpp_results = rxpp_objects["ObjectList"].split(" ")

        for result in rxpp_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_arpnd_results(self, name: str):
        results = []

        # Get specific analyzer object
        arpnd_objects = self._stc.perform("getObjects", className="ArpNdResults")
        arpnd_results = arpnd_objects["ObjectList"].split(" ")

        for result in arpnd_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_port_latency_results(self, name: str):
        results = []

        # Get specific analyzer object
        latency_objects = self._stc.perform("getObjects", className="PortAvgLatencyResults")
        latency_results = latency_objects["ObjectList"].split(" ")

        for result in latency_results:
            results.append(self._stc.get(result, name))

        return results

    def stc_set_fec(self, fec=True):
        """
        Set FEC (forward error correction) in xml configuration.
        """
        xpath = ["StcSystem/Project/Port/Ethernet100GigFiber"]
        fec_handler = self.stc_object_xpath(xpath)

        self.stc_attribute(fec_handler, "ForwardErrorCorrection", str(fec))

    def stc_get_link_status(self) -> str:
        """Get link status from the spirent point of view.

        Returns
        -------
        str
            Link status, one of the folowing:
            "DOWN" Link is down.
            "UP" Link is up.
            "ERROR" Link has error.
            "ADMIN_DOWN" Link is administratively down.
            "UP_SW_DISABLED" The link is up, but is disabled by software.
            "SONET" Link is SONET.
            "NONE" No link present.
        """

        project_ports = self._stc.get("project1", "children-Port")
        phy_command = self._stc.perform("PortSetupGetActivePhyCommand", port=project_ports)
        return self._stc.get(phy_command["ActivePhy"], "LinkStatus")
