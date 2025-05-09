"""
Comparse, parsing at scale

Unlicense (CC0, Public Domain) Allie H, 2025

This is a library for idiomatic parsing of complex string structures in Python.
It is optimized to be easy to expand upon for large files and complex structures while retaining minimal overhead.
"""

__all__ = [
    "abstract",
    "parser",
    "walk",
    "generator",
]

from . import abstract
from . import parser
from . import walk
from . import generator