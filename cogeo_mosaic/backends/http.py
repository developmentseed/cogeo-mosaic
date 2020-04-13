import functools
import json
from typing import Dict, Optional, Tuple, Union

import mercantile
import requests

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _decompress_gz, get_assets_from_json
from cogeo_mosaic.model import MosaicJSON


class HttpBackend(BaseBackend):
    """Http/Https Backend Adapter"""

    def __init__(self, url: str, mosaic_def: Optional[Union[MosaicJSON, Dict]] = None):
        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read_mosaic(url)

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""

        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def upload(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read_mosaic(self, url: str) -> MosaicJSON:
        """Get Mosaic definition info."""
        body = requests.get(url).content

        if url.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
