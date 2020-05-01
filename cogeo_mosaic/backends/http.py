"""cogeo-mosaic HTTP backend."""

import functools
import json
from typing import Any, Dict, List, Optional, Union

import mercantile
import requests

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _decompress_gz, get_assets_from_json
from cogeo_mosaic.mosaic import MosaicJSON


class HttpBackend(BaseBackend):
    """Http/Https Backend Adapter"""

    def __init__(
        self,
        url: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        **kwargs: Any
    ):
        """Initialize HttpBackend."""
        self.path = url

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self._read(**kwargs)

    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self):
        """Write mosaicjson document."""
        raise NotImplementedError

    def update(self, *args, **kwargs: Any):
        """Update the mosaicjson document."""
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def _read(self, gzip: bool = None) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        body = requests.get(self.path).content

        if gzip or (gzip is None and self.path.endswith(".gz")):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
