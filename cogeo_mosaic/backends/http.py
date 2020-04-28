"""cogeo-mosaic HTTP backend."""

from typing import Any, Callable, Dict, List, Optional, Sequence, Union

import json
import warnings
import functools

import requests
import mercantile

from cogeo_mosaic.mosaic import MosaicJSON, DEFAULT_ACCESSOR
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _decompress_gz, get_assets_from_json


class HttpBackend(BaseBackend):
    """Http/Https Backend Adapter"""

    def __init__(
        self,
        url: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        **kwargs: Any
    ):
        """Initialize HttpBackend."""
        self.url = url

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

    def update(
        self,
        features: Sequence[Dict],
        accessor: Callable = DEFAULT_ACCESSOR,
        overwrite: bool = False,
        **kwargs: Any
    ):
        """Update the mosaicjson document."""
        self._update(features, accessor, **kwargs)
        if overwrite:
            warnings.warn("Overwrite is not possible for http backend")

    @functools.lru_cache(maxsize=512)
    def _read(self, gzip: bool = None) -> MosaicJSON:
        """Get mosaicjson document."""
        body = requests.get(self.url).content

        if gzip or (gzip is None and self.url.endswith(".gz")):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))
