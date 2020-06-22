"""cogeo-mosaic STAC backend."""

import functools
import json
from typing import Any, Callable, Dict, List, Optional

import mercantile
import requests

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import get_assets_from_json
from cogeo_mosaic.mosaic import MosaicJSON


def default_stac_accessor(feature: Dict):
    """Return specific feature identifier."""
    link = list(filter(lambda link: link["rel"] == "self", feature["links"]))[0]
    return link["href"]


class STACBackend(BaseBackend):
    """STAC Backend Adapter"""

    _backend_name = "STAC"

    def __init__(
        self, url: str, minzoom: int, maxzoom: int, query: Dict = {}, **kwargs: Any
    ):
        """Initialize HttpBackend."""
        self.path = url
        self.mosaic_def = self._read(json.dumps(query), minzoom, maxzoom, **kwargs)

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

    def _read(  # type: ignore
        self,
        query: str,
        minzoom: int,
        maxzoom: int,
        accessor: Callable = default_stac_accessor,
        max_items: Optional[int] = None,
        **kwargs: Any
    ) -> MosaicJSON:
        """Fetch STAC API and construct the mosaicjson."""
        features = stac_search(self.path, json.dumps(query), max_items=max_items)

        return MosaicJSON.from_features(
            features, minzoom, maxzoom, accessor=accessor, **kwargs
        )


@functools.lru_cache(maxsize=512)
def stac_search(
    stac_url: str, query: Dict = {}, max_items: Optional[int] = None
) -> List[Dict]:
    """Query STAC Search."""
    features: List[Dict] = []

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Accept": "application/geo+json",
    }

    def _fetch(url):
        return requests.post(url, headers=headers, data=query).json()

    next_url = stac_url
    while True:
        results = _fetch(next_url)
        if results["context"]["returned"] == 0:
            break

        features.extend(results["features"])
        if max_items and len(features) >= max_items:
            break

        link = list(filter(lambda link: link["rel"] == "next", results["links"]))
        if not link:
            break

        next_url = link[0]["href"]

    return features
