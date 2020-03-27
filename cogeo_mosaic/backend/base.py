"""cogeo_mosaic.backend.base: base Backend class."""

import abc
from contextlib import AbstractContextManager
from typing import Dict


class BaseBackend(AbstractContextManager):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Load resource"""
        self.quadkey_zoom: Optional[int]
        self.mosaic_def: Dict

    def metadata(self) -> Dict:
        """Retrieve Mosaic metadata

        Returns
        -------
        MosaicJSON as dict without `tiles` key.
        """
        return {k: v for k, v in self.mosaic_def.items() if k != "tiles"}

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
