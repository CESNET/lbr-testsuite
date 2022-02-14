# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# sys.path.insert(0, os.path.abspath('.'))

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2].absolute()))

# Mock certain imports to prevent import errors during documentation build.
autodoc_mock_imports = ['tkinter']

# -- Project information -----------------------------------------------------

project = 'lbr_testsuite package'
copyright = '2021 CESNET, z.s.p.o.'
author = 'Dominik Tran <tran@cesnet.cz>'

# The full version, including alpha/beta/rc tags
release = '1.0'


# -- General configuration ---------------------------------------------------

# Default value is "members,undoc-members, show-inheritance". This line supresses
# document generation for members causing following warning during build:
#      "WARNING: duplicate object description of XXX, other instance in YYY,
#      "use :noindex: for one of them"
os.environ["SPHINX_APIDOC_OPTIONS"] = "members,show-inheritance"

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.githubpages',
    'sphinxcontrib.apidoc',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# Note: No effect when using sphinx-apidoc
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['css']

html_css_files = [
    'one_parameter_per_line.css',
]

# -- Configuration for sphinxcontrib-apidoc extension ------------------------

apidoc_module_dir = str(Path(__file__).parents[2])
apidoc_output_dir = str(Path(__file__).parents[0] / 'sources')
apidoc_excluded_paths = ['framework', 'setup.py']
apidoc_separate_modules = True
apidoc_module_first = True
