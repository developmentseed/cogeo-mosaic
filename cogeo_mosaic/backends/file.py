"""cogeo-mosaic File backend."""

import json
from typing import Any, Dict, List, Optional, Union

import mercantile
from cachetools.keys import hashkey
from rio_tiler.io import BaseReader, COGReader

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)
from cogeo_mosaic.cache import lru_cache
from cogeo_mosaic.errors import _FILE_EXCEPTIONS, MosaicError
from cogeo_mosaic.mosaic import MosaicJSON


class FileBackend(BaseBackend):
    """Local File Backend Adapter"""

    _backend_name = "File"

    def __init__(
        self,
        path: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        reader: BaseReader = COGReader,
        **kwargs: Any,
    ):
        """Initialize FileBackend."""
        self.path = path
        self.reader = reader

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self._read(**kwargs)

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self, gzip: bool = None):
        """Write mosaicjson document to a file."""
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
