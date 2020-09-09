"""cogeo-mosaic File backend."""

import json
import os
from typing import List

import attr
import mercantile
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)
from cogeo_mosaic.cache import lru_cache
from cogeo_mosaic.errors import _FILE_EXCEPTIONS, MosaicError, MosaicExists
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class FileBackend(BaseBackend):
    """Local File Backend Adapter"""

    _backend_name = "File"

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self, overwrite: bool = False, gzip: bool = None):
        """Write mosaicjson document to a file."""
        if not overwrite and os.path.exists(self.path):
            raise MosaicExists("Mosaic file already exist, use `overwrite=True`.")

        body = self.mosaic_def.dict(exclude_none=True)
        with open(self.path, "wb") as f:
            try:
                if gzip or (gzip is None and self.path.endswith(".gz")):
                    f.write(_compress_gz_json(body))
                else:
                    f.write(json.dumps(body).encode("utf-8"))
            except Exception as e:
                exc = _FILE_EXCEPTIONS.get(e, MosaicError)  # type: ignore
                raise exc(str(e)) from e

    @lru_cache(key=lambda self, gzip=None: hashkey(self.path, gzip),)
    def _read(self, gzip: bool = None) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        try:
            with open(self.path, "rb") as f:
                body = f.read()
        except Exception as e:
            exc = _FILE_EXCEPTIONS.get(e, MosaicError)  # type: ignore
            raise exc(str(e)) from e

        self._file_byte_size = len(body)

        if gzip or (gzip is None and self.path.endswith(".gz")):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
