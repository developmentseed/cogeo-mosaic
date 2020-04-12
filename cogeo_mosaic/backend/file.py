import functools
import json
from typing import Dict, Optional, Tuple

import mercantile

from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import (_compress_gz_json, _decompress_gz,
                                        get_assets_from_json)
from cogeo_mosaic.model import MosaicJSON


class FileBackend(BaseBackend):
    """Local File Backend Adapter"""

    def __init__(
        self, path: str, mosaic_def: Optional[MosaicJSON] = None,
    ):
        self.path = path
        self.mosaic_def = mosaic_def or self.read_mosaic(path)

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""

        return get_assets_from_json(
            self.mosaic_def["tiles"], self.quadkey_zoom, x, y, z
        )

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def["tiles"], self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def upload(self):
        with open(self.path, "wb") as f:
            f.write(_compress_gz_json(self.mosaic_def))

    def update(self):
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read_mosaic(self, path: str) -> Dict:
        """Get Mosaic definition info."""
        with open(path, "rb") as f:
            body = f.read()

        if path.endswith(".gz"):
            body = _decompress_gz(body)

        return json.loads(body)
