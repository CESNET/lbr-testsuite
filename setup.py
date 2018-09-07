try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

setup(
	name='spirent',
	version='1.0',
	description='Spirent Test Center tools',
	packages=['spirent', 'spirent.stcapi']
)
