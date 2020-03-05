try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='spirent',
    version='1.0',
    author='Pavel Krobot, Jan Drazil',
    author_email='pavel.krobot@cesnet.cz, jan.drazil@cesnet.cz',
    description='Spirent Test Center tools',
    packages=['spirent', 'spirent.stcapi'],
)
