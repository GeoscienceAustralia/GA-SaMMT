# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Geoscience Australia's Semi-automated Morphological Mapping Tools (GA-SaMMT)"
copyright = "2023, Geoscience Australia"
author = "Marine and Coastal Geoscience Team"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinxcontrib.bibtex",
]
bibtex_bibfiles = ["references.bib"]
bibtex_reference_style = "author_year"

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for LaTeX output -------------------------------------------------
# latex_logo = "images/test-image.png"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "nature"
html_static_path = ["_static"]
