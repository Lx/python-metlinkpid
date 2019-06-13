import os
import sys

sys.path.insert(0, os.path.abspath('..'))

project = 'metlinkpid Python Module'
version = release = '1.0.0'
# noinspection PyShadowingBuiltins
copyright = '2019, Alex Peters'
author = 'Alex Peters'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
]
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pyserial': ('https://pyserial.readthedocs.io/en/latest', None),
}

master_doc = 'index'

html_theme = 'sphinx_rtd_theme'
html_show_sourcelink = False
html_last_updated_fmt = '%d %B %Y'
html_show_sphinx = False
html_theme_options = {
    'style_external_links': True,
}
