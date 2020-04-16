"""cogeo-mosaic File backend."""

from typing import Dict, Optional, Tuple, Union

import json
import functools

import mercantile

from cogeo_mosaic.model import MosaicJSON
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)


class FileBackend(BaseBackend):
    """Local File Backend Adapter"""

    def __init__(self, path: str, mosaic_def: Optional[Union[MosaicJSON, Dict]] = None):
        """Initialize FileBackend."""
        self.path = path

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read()

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self, gzip=None):
        """Write mosaicjson document to a file."""
        body = dict(self.mosaic_def)
        if gzip or (gzip is None and self.path.endswith(".gz")):
            body = _compress_gz_json(body)
        else:
            body = json.dumps(body).encode("utf-8")

        with open(self.path, "wb") as f:
            f.write(body)

    def update(self):
        """Update the mosaicjson document."""
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read(self) -> MosaicJSON:
        """Get mosaicjson document."""
        with open(self.path, "rb") as f:
            body = f.read()

        if self.path.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
