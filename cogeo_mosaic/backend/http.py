import functools
import json
from typing import Dict, Tuple

import mercantile
import requests
from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import get_assets_from_json
from cogeo_mosaic.utils import _decompress_gz


class HttpBackend(BaseBackend):
    """Http/Https Backend Adapter"""

    def __init__(self, url: str):
        self.mosaic_def = self.fetch_mosaic_definition(url)

    def tile(self, x: int, y: int, z: int, bucket: str, key: str) -> Tuple[str]:
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

    @functools.lru_cache(maxsize=512)
    def fetch_mosaic_definition(self, url: str) -> Dict:
        """Get Mosaic definition info."""
        body = requests.get(url).content

        if url.endswith(".gz"):
            body = _decompress_gz(body)

        return json.loads(body)
