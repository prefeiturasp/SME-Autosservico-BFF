"""Sphinx configuration for the SME Autosservico BFF documentation."""

import os
import sys

import django

sys.path.insert(0, os.path.abspath(".."))

os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

project = "SME-Autosservico-BFF"
copyright = "2026, SME"
author = "SME"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
