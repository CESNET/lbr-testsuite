try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

setup(
	name='spirent',
	version='1.0',
	author='Jan Drazil, Ivan Hazucha',
	author_email='jan.drazil@cesnet.cz, xhazuc00@fit.vutbr.cz',
	description='Spirent Test Center tools',
	packages=['spirent', 'spirent.stcapi'],
)
