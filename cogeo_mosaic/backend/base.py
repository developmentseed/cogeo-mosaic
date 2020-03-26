"""cogeo_mosaic.backend.base: base Backend class."""

import abc
import contextlib
from typing import Dict


class BaseBackend(metaclass=contextlib.AbstractContextManager):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Load resource"""

    @abc.abstractmethod
    def metadata(self):
        """Retrieve MosaicJSON metadata."""

    @abc.abstractmethod
    def tile(self, x: int, y: int, z: int):
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def point(self, lng: float, lat: float):
        """Retrieve assets for point."""

    @abc.abstractmethod
    def create(self, mosaic: Dict):
        """Upload new MosaicJSON to backend."""

    @abc.abstractmethod
    def update(self, mosaic: Dict):
        """Update existing MosaicJSON on backend."""
