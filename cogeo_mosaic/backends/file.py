import functools
import json
from typing import Dict, Optional, Tuple, Union

import mercantile

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)
from cogeo_mosaic.model import MosaicJSON


class FileBackend(BaseBackend):
    """Local File Backend Adapter"""

    def __init__(
        self, path: str, mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
    ):
        self.path = path
        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read(path)

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""

        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self):
        with open(self.path, "wb") as f:
            f.write(_compress_gz_json(dict(self.mosaic_def)))

    def update(self):
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read(self, path: str) -> MosaicJSON:
        """Get Mosaic definition info."""
        with open(path, "rb") as f:
            body = f.read()

        if path.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
