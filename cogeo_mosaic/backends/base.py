"""cogeo_mosaic.backend.base: base Backend class."""

from typing import Dict, List

import abc
from contextlib import AbstractContextManager

from cogeo_mosaic.model import MosaicJSON
from cogeo_mosaic.backends.utils import get_hash


class BaseBackend(AbstractContextManager):
    """Base Class for cogeo-mosaic backend storage."""

    mosaic_def: MosaicJSON

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Connect to backend"""

    def __enter__(self):
        """Support using with Context Managers"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers"""

    @property
    def metadata(self) -> Dict:
        """Retrieve Mosaic metadata

        Returns
        -------
        MosaicJSON as dict without `tiles` key.
        """
        return {k: v for k, v in dict(self.mosaic_def).items() if k != "tiles"}

    @abc.abstractmethod
    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""

    @abc.abstractmethod
    def read(self) -> MosaicJSON:
        """Fetch mosaic definition"""

    @property
    def mosaicid(self) -> str:
        """Return sha224 id of the mosaicjson document."""
        return get_hash(**dict(self.mosaic_def))

    @property
    def quadkey_zoom(self) -> int:
        """Return Quadkey zoom property."""
        return self.mosaic_def.quadkey_zoom or self.mosaic_def.minzoom

    @abc.abstractmethod
    def write(self):
        """Upload new MosaicJSON to backend."""

    @abc.abstractmethod
    def update(self):
        """Update existing MosaicJSON on backend."""
