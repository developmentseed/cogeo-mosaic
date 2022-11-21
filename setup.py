"""Fake cogeo-mosaic setup.py for github."""
import sys

from setuptools import setup

sys.stderr.write(
    """
===============================
Unsupported installation method
===============================
cogeo-mosaic no longer supports installation with `python setup.py install`.
Please use `python -m pip install .` instead.
"""
)
sys.exit(1)


# The below code will never execute, however GitHub is particularly
# picky about where it finds Python packaging metadata.
# See: https://github.com/github/feedback/discussions/6456
#
# To be removed once GitHub catches up.

setup(
    name="cogeo-mosaic",
    install_requires=[
        "attrs",
        "morecantile>=3.1,<4.0",
        "shapely>=2.0b2,<2.1",
        "pydantic",
        "httpx",
        "rasterio",
        "rio-tiler>=4.0.0a0,<5.0",
        "cachetools",
        "supermercado",
    ],
)
