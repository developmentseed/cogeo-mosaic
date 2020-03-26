"""cogeo_mosaic.backend.base: base Backend class."""

import abc
import contextlib


class BaseBackend(metaclass=contextlib.AbstractContextManager):
    @abc.abstractmethod
    def __enter__(self, *args, **kwargs):
        """Load resource"""

    @abc.abstractmethod
    def metadata(self, *args, **kwargs):
        """Retrieve MosaicJSON metadata."""

    @abc.abstractmethod
    def tile(self, x: int, y: int, z: int, *args, **kwargs):
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def point(self, lng: float, lat: float, *args, **kwargs):
        """Retrieve assets for point."""

    @abc.abstractmethod
    def create(self, *args, **kwargs):
        """Upload new MosaicJSON to backend."""

    @abc.abstractmethod
    def update(self, *args, **kwargs):
        """Update existing MosaicJSON on backend."""
