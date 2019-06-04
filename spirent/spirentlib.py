from spirent.stcapi.StcPythonTCP import StcPythonTCP

import re
import pprint


class StcHandler:
	"""Basic STC configuration class"""

	def __init__(self):
		self._stc = None
		self._generator_port_results = None
		self._analyzer_port_results = None
		self._filtered_stream_results = None
		self._rx_stream_block_results = None
		self._tx_stream_block_results = None

	def stc_api_connect(self, host: str, port: int):
		self._stc = StcPythonTCP(host, port)

	def stc(self):
		return self._stc

	def stc_init(self, xml_config_file: str):
		self.logging_config()
		self.load_xml(xml_config_file)
		self.set_sequencer()
		self.subscribe_to_results()

		# Always delete streams from analyzers
		xpath = self.stc_object_xpath('StcSystem/Project/ResultOptions')
		self.stc_attribute(xpath, 'DeleteAllAnalyzerStreams', 'TRUE')

		# Apply config
		self._stc.apply()

	def logging_config(self, level='error', file='stdout'):
		# Possible logLevel values are: DEBUG, INFO, WARN, and ERROR
		# Possible values for logTo are "stdout" or a file name (can include
		# the path). Use forward slashes between directory names.
		self._stc.config('automationoptions', logLevel=level, logTo=file)

	def load_xml(self, xml_config_file: str):
		"""Load XML config using string format"""
		with open(xml_config_file, 'rb') as file:
			config_string = file.read()
		return self._stc.perform('loadfromxml', FileName='', InputConfigString=config_string)

	def set_sequencer(self):
		sequencer = self._stc.get('system1', 'children-sequencer')
		self._stc.config(sequencer, errorHandler='stop_on_error')

	def subscribe_to_results(self):
		project = self._stc.get('system1', 'children-Project')

		self._generator_port_results = self.sub_generator_port_results(project)
		self._analyzer_port_results = self.sub_analyzer_port_results(project)
		self._filtered_stream_results = self.sub_filtered_stream_results(project)
		self._rx_stream_block_results = self.sub_rx_stream_block_results(project)
		self._tx_stream_block_results = self.sub_tx_stream_block_results(project)

	def sub_generator_port_results(self, parent: str):
		generator_port_results = self._stc.subscribe(
			parent=parent,
			resultParent=parent,
			configType='generator',
			resultType='generatorportresults',
			filterList='',
			disablePaging='true',
			recordsPerPage=256,
			viewAttributeList='totalframecount totaloctetcount generatorframecount generatoroctetcount generatorsigframecount generatorundersizeframecount generatoroversizeframecount generatorjumboframecount totalframerate totaloctetrate generatorframerate generatoroctetrate generatorsigframerate generatorundersizeframerate generatoroversizeframerate generatorjumboframerate generatorcrcerrorframecount generatorl3checksumerrorcount generatorl4checksumerrorcount generatorcrcerrorframerate generatorl3checksumerrorrate generatorl4checksumerrorrate totalipv4framecount totalipv6framecount totalmplsframecount generatoripv4framecount generatoripv6framecount generatorvlanframecount generatormplsframecount totalipv4framerate totalipv6framerate totalmplsframerate generatoripv4framerate generatoripv6framerate generatorvlanframerate generatormplsframerate totalbitrate generatorbitrate l1bitcount l1bitrate pfcframecount pfcpri0framecount pfcpri1framecount pfcpri2framecount pfcpri3framecount pfcpri4framecount pfcpri5framecount pfcpri6framecount pfcpri7framecount l1bitratepercent ',
			interval=1
		)
		return generator_port_results

	def sub_analyzer_port_results(self, parent: str):
		analyzer_port_results = self._stc.subscribe(
			parent=parent,
			configType='analyzer',
			resultType='analyzerportresults',
			filterList='',
			disablePaging='true',
			recordsPerPage=256,
			viewAttributeList='totalframecount totaloctetcount sigframecount undersizeframecount oversizeframecount jumboframecount minframelength maxframelength pauseframecount totalframerate totaloctetrate sigframerate undersizeframerate oversizeframerate jumboframerate pauseframerate fcserrorframecount ipv4checksumerrorcount tcpchecksumerrorcount udpchecksumerrorcount prbsfilloctetcount prbsbiterrorcount fcserrorframerate ipv4checksumerrorrate tcpchecksumerrorrate udpchecksumerrorrate prbsfilloctetrate prbsbiterrorrate ipv4framecount ipv6framecount ipv6overipv4framecount tcpframecount udpframecount mplsframecount icmpframecount vlanframecount ipv4framerate ipv6framerate ipv6overipv4framerate tcpframerate udpframerate mplsframerate icmpframerate vlanframerate trigger1count trigger1rate trigger2count trigger2rate trigger3count trigger3rate trigger4count trigger4rate trigger5count trigger5rate trigger6count trigger6rate trigger7count trigger7rate trigger8count trigger8rate combotriggercount combotriggerrate totalbitrate prbsbiterrorratio vlanframerate l1bitcount l1bitrate pfcframecount fcoeframecount pfcframerate fcoeframerate pfcpri0framecount pfcpri1framecount pfcpri2framecount pfcpri3framecount pfcpri4framecount pfcpri5framecount pfcpri6framecount pfcpri7framecount pfcpri0quanta pfcpri1quanta pfcpri2quanta pfcpri3quanta pfcpri4quanta pfcpri5quanta pfcpri6quanta pfcpri7quanta prbserrorframecount prbserrorframerate userdefinedframecount1 userdefinedframerate1 userdefinedframecount2 userdefinedframerate2 userdefinedframecount3 userdefinedframerate3 userdefinedframecount4 userdefinedframerate4 userdefinedframecount5 userdefinedframerate5 userdefinedframecount6 userdefinedframerate6 l1bitratepercent outseqframecount ',
			interval=1
		)
		return analyzer_port_results

	def sub_filtered_stream_results(self, parent: str):
		port = self._stc.get('system1.Project(1)', 'children-Port')
		filtered_stream_results = self._stc.subscribe(
			parent=parent,
			resultParent=port,
			configType='analyzer',
			resultType='filteredstreamresults',
			filterList='',
			disablePaging='true',
			recordsPerPage=256,
			viewAttributeList='streamindex framecount sigframecount fcserrorframecount minlatency maxlatency seqrunlength droppedframecount droppedframepercent inorderframecount reorderedframecount duplicateframecount lateframecount prbsbiterrorcount prbsfilloctetcount ipv4checksumerrorcount tcpudpchecksumerrorcount framerate sigframerate fcserrorframerate droppedframerate droppedframepercentrate inorderframerate reorderedframerate duplicateframerate lateframerate prbsbiterrorrate ipv4checksumerrorrate tcpudpchecksumerrorrate filteredvalue_1 filteredvalue_2 filteredvalue_3 filteredvalue_4 filteredvalue_5 filteredvalue_6 filteredvalue_7 filteredvalue_8 filteredvalue_9 filteredvalue_10 bitrate shorttermavglatency avglatency prbsbiterrorratio bitcount l1bitcount l1bitrate prbserrorframecount prbserrorframerate shorttermavgjitter avgjitter minjitter maxjitter shorttermavginterarrivaltime avginterarrivaltime mininterarrivaltime maxinterarrivaltime lastseqnum inseqframecount outseqframecount inseqframerate outseqframerate histbin1count histbin2count histbin3count histbin4count histbin5count histbin6count histbin7count histbin8count histbin9count histbin10count histbin11count histbin12count histbin13count histbin14count histbin15count histbin16count ',
			interval=1
		)
		return filtered_stream_results

	def sub_rx_stream_block_results(self, parent: str):
		rx_stream_block_results = self._stc.subscribe(
			parent=parent,
			resultParent=parent,
			configType='streamblock',
			resultType='rxstreamblockresults',
			filterList='',
			disablePaging='true',
			recordsPerPage=256,
			viewAttributeList='framecount framerate bitrate sigframecount fcserrorframecount minlatency maxlatency droppedframecount droppedframepercent inorderframecount reorderedframecount duplicateframecount lateframecount prbsbiterrorcount prbsfilloctetcount ipv4checksumerrorcount tcpudpchecksumerrorcount avglatency prbsbiterrorratio prbserrorframecount rxportname avgjitter minjitter maxjitter avginterarrivaltime mininterarrivaltime maxinterarrivaltime inseqframecount outseqframecount histbin1count histbin2count histbin3count histbin4count histbin5count histbin6count histbin7count histbin8count histbin9count histbin10count histbin11count histbin12count histbin13count histbin14count histbin15count histbin16count ',
			interval=1
		)
		return rx_stream_block_results

	def sub_tx_stream_block_results(self, parent: str):
		tx_stream_block_results = self._stc.subscribe(
			parent=parent,
			resultParent=parent,
			configType='streamblock',
			resultType='txstreamblockresults',
			filterList='',
			disablePaging='true',
			recordsPerPage=256,
			viewAttributeList='framecount framerate bitrate',
			interval=1
		)
		return tx_stream_block_results

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
			elements = xpath.split('/')

			for element in elements:
				# print('Processing element: {}'.format(element))
				# Split parts of the element term
				parts = re.findall(r"[^\[\]]+", element)
				# Extract name of the element
				name = parts.pop(0)
				# Find children
				if len(heap) == 0:
					# print('Heap_len is 0: getting object {}'.format(name))
					result = self._stc.perform('GetObjects', classname=name)
					object_list = result['ObjectList']
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
						child = self._stc.get(item, 'children-' + name)
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
						condition = part.split('=')
						left_val = condition[0]
						right_val = condition[1]

						# Attribute value condition
						if left_val[0] == '@':
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

	def stc_attribute(self, handles, attributes, values=''):
		if values == '':
			return self.stc_get_attributes(handles, attributes)
		else:
			self.stc_set_attributes(handles, attributes, values)

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
				if name == '*':
					values.append(self._stc.get(subhandle))
				else:
					values.append(self._stc.get(subhandle, name))

			results.append(values)

		return results

	def stc_set_attributes(self, handles, attributes, values):
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

		# Apply config
		self._stc.apply()

	def stc_attribute_xpath(self, xpaths, values=''):
		# Handle single xpath as a list with 1 member
		if type(xpaths) == str:
			xpaths = xpaths.split()

		attributes = []
		object_xpaths = []

		for xpath in xpaths:
			object_xpath, attribute = xpath.rsplit('/', 1)
			object_xpaths.append(object_xpath)
			attributes.append(attribute)

		# Get object handles
		handles = self.stc_object_xpath(object_xpaths)

		# Get/Set values
		return self.stc_attribute(handles, attributes, values)

	def stc_connect(self, host: str, ports: str):
		port_list = ports.split(' ')

		if len(port_list) == 0:
			return

		stc_port_objects = self._stc.perform(
			'getObjects', classname='Port', condition='isVirtual=false')
		stc_port_object_list = stc_port_objects['ObjectList']
		stc_port_object_list = stc_port_object_list.split(' ')

		for stc_port in stc_port_object_list:
			# Set proper //host/slot/port format
			location_string = '//{}/{}'.format(host, port_list.pop(0))
			self._stc.config(stc_port, location=location_string)
			self._stc.config(stc_port, name=location_string)

		# Apply settings
		self._stc.apply()

		# Perform the logical to physical port mapping, connect to the chassis and reserve the ports
		project_ports = self._stc.get('project1', 'children-Port')
		self._stc.perform('attachPorts', autoconnect='true', portlist=project_ports)

	def stc_disconnect(self):
		self._stc.perform('chassisDisconnectAll')
		self._stc.perform('resetConfig')

	def stc_start_arpnd(self):
		project_ports = self._stc.get('project1', 'children-Port')
		self._stc.perform('ArpNdStartCommand', handleList=project_ports)

	def stc_start_generators(self):
		# Set logging
		self.logging_config()

		# Get all generator handles
		generator_objects = self._stc.perform('getObjects', classname='Generator')
		generators = generator_objects['ObjectList'].split(' ')

		# Get continuous generators handles only
		continuous_generators = []
		for generator in generators:
			gen_duration_mode = self._stc.get(
				'{}.generatorConfig'.format(generator), 'durationMode')
			if gen_duration_mode == 'CONTINUOUS':
				continuous_generators.append(generator)

		# Start generators and wait 1 second
		self._stc.perform('generatorStart', generatorList=generators)
		if len(continuous_generators) != 0:
			self._stc.perform('generatorWaitForStart', generatorList=continuous_generators)
		self._stc.perform('wait', waitTime=1)

	def stc_stop_generators(self):
		# Get all generator handles
		generator_objects = self._stc.perform('getObjects', classname='Generator')
		generators = generator_objects['ObjectList'].split(' ')

		# Get continuous generators handles only
		continuous_generators = []
		for generator in generators:
			gen_duration_mode = self._stc.get(
				'{}.generatorConfig'.format(generator), 'durationMode')
			if gen_duration_mode == 'CONTINUOUS':
				continuous_generators.append(generator)

		# Stop generators and wait 1 second
		if len(continuous_generators) != 0:
			self._stc.perform('generatorStop', generatorList=continuous_generators)
		self._stc.perform('generatorWaitForStop', generatorList=generators)
		self._stc.perform('wait', waitTime=1)

	def stc_start_analyzers(self):
		# Get all analyzer handles
		analyzer_objects = self._stc.perform('getObjects', className='Analyzer')
		analyzers = analyzer_objects['ObjectList'].split(' ')

		# Start analyzers and wait 1 second
		self._stc.perform('analyzerStart', analyzerList=analyzers)
		self._stc.perform('wait', waitTime=1)

	def stc_stop_analyzers(self):
		# Get all analyzer handles
		analyzer_objects = self._stc.perform('getObjects', className='Analyzer')
		analyzers = analyzer_objects['ObjectList'].split(' ')

		# Stop analyzers and wait 1 second
		self._stc.perform('analyzerStop', analyzerList=analyzers)
		self._stc.perform('wait', waitTime=1)

	def stc_refresh_results(self):
		self._stc.perform('RefreshResultView', resultDataSet=self._rx_stream_block_results)
		self._stc.perform('RefreshResultView', resultDataSet=self._tx_stream_block_results)

	def stc_clear_results(self):
		ports = self._stc.get('project1', 'children-Port')
		self._stc.perform('ResultsClearAll', portList=ports)

	def stc_stream_block(self, names='*'):
		# Handle default input
		if type(names) == str:
			names = [x for x in names.split()]

		xpaths = []

		for name in names:
			xpaths.append("StcSystem/Project/Port/StreamBlock[@Name={}]".format(name))

		return self.stc_object_xpath(xpaths)

	def stc_tx_stream_block_results(self, stream_blocks, names='*'):
		result_handles = self.stc_attribute(stream_blocks, "children-TxStreamBlockResults")
		return self.stc_attribute(result_handles, names)

	def stc_rx_stream_block_results(self, stream_blocks, names='*'):
		result_handles = self.stc_attribute(stream_blocks, "children-RxStreamBlockResults")
		return self.stc_attribute(result_handles, names)

	def stc_filtered_stream_results(self, names='*'):
		if type(names) == str:
			names = [x for x in names.split()]
		results = []
		total_page_count = self.stc_attribute([[self._filtered_stream_results]], 'TotalPageCount')
		for page in range(1, int(total_page_count[0][0]) + 1):
			# Set page
			self.stc_attribute([[self._filtered_stream_results]], 'PageNumber', str(page))
			# Find specific object
			objects = self._stc.perform('getObjects', className='FilteredStreamResults')
			filtered_stream_results = objects['ObjectList'].split(' ')
			results.append(self.stc_attribute([filtered_stream_results], names))

		return results

	def stc_analyzer_filter(self, values=''):
		objects = self._stc.perform('getObjects', className='AnalyzerFrameConfigFilter')
		analyzer_frame_config_filters = objects['ObjectList'].split(' ')

		# Get or set
		if values == '':
			return self.stc_attribute([analyzer_frame_config_filters], 'FrameConfig')
		else:
			return self.stc_attribute([analyzer_frame_config_filters], 'FrameConfig', values)

	def stc_generator_port_results(self, name: str):
		results = []

		# Get specific generator object
		generator_objects = self._stc.perform('getObjects', className='GeneratorPortResults')
		generator_port_results = generator_objects['ObjectList'].split(' ')

		for result in generator_port_results:
			results.append(self._stc.get(result, name))

		return results

	def stc_analyzer_port_results(self, name: str):
		results = []

		# Get specific analyzer object
		analyzer_objects = self._stc.perform('getObjects', className='AnalyzerPortResults')
		analyzer_port_results = analyzer_objects['ObjectList'].split(' ')

		for result in analyzer_port_results:
			results.append(self._stc.get(result, name))

		return results

	@property
	def stc(self):
		return self._stc
