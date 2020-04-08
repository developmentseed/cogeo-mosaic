"""cogeo_mosaic.backend.base: base Backend class."""

import abc
from contextlib import AbstractContextManager
from typing import Dict, Optional

from cogeo_mosaic import version as mosaic_version
from cogeo_mosaic.backend.utils import get_hash
from cogeo_mosaic.utils import create_mosaic


class BaseBackend(AbstractContextManager):
    mosaic_def: Optional[Dict]

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Connect to backend"""

    def __enter__(self):
        """Support using with Context Managers"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers"""

    def metadata(self) -> Dict:
        """Retrieve Mosaic metadata

        Returns
        -------
        MosaicJSON as dict without `tiles` key.
        """
        if self.mosaic_def is None:
            return {}

        return {k: v for k, v in self.mosaic_def.items() if k != "tiles"}

    @abc.abstractmethod
    def tile(self, x: int, y: int, z: int):
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def point(self, lng: float, lat: float):
        """Retrieve assets for point."""

    def create(self, *args, **kwargs):
        """Create new MosaicJSON and upload to backend."""

        self.mosaic_def = create_mosaic(*args, **kwargs)
        self.upload(self.mosaic_def)

    @property
    def mosaicid(self) -> str:
        return get_hash(body=self.mosaic_def, version=mosaic_version)

    @property
    def quadkey_zoom(self) -> Optional[int]:
        if self.mosaic_def:
            return self.mosaic_def.get("quadkey_zoom", self.mosaic_def["minzoom"])

        return None

    @abc.abstractmethod
    def upload(self, mosaic: Dict):
        """Upload new MosaicJSON to backend."""

    # Commented to allow child classes to not implement this
    # @abc.abstractmethod
    def update(self, mosaic: Dict):
        """Update existing MosaicJSON on backend."""
