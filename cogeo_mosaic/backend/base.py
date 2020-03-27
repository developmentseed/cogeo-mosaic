"""cogeo_mosaic.backend.base: base Backend class."""

import abc
import contextlib
from typing import Dict


class BaseBackend(metaclass=contextlib.AbstractContextManager):
    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Load resource"""

    def metadata(self, tiles: bool = False) -> Dict:
        """Retrieve Mosaic metadata

        Attributes
        ----------
        tiles: bool, optional
            Include `tiles` key in response. Note, for some backends this may
            not exist.

        Returns
        -------
        MosaicJSON as dict. If `tiles` is `True`, includes the `tiles` key in
        the MosaicJSON; otherwise it excludes it.
        """
        if tiles:
            if "tiles" not in self.mosaic_def.keys():
                raise ValueError("Requested tiles for unsupported backend")
            return self.mosaic_def

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
