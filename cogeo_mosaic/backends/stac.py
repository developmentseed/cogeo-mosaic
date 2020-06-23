"""cogeo-mosaic STAC backend."""

import functools
import json
import os
from typing import Any, Callable, Dict, List, Optional

import mercantile
import requests

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import get_assets_from_json
from cogeo_mosaic.mosaic import MosaicJSON


def default_stac_accessor(feature: Dict):
    """Return feature identifier."""
    link = list(filter(lambda link: link["rel"] == "self", feature["links"]))
    if link:
        return link[0]["href"]

    link = list(filter(lambda link: link["rel"] == "root", feature["links"]))
    if link:
        return os.path.join(
            link[0]["href"],
            "collections",
            feature["collection"],
            "items",
            feature["id"],
        )

    # Fall back to the item ID
    return feature["id"]


class STACBackend(BaseBackend):
    """STAC Backend Adapter"""

    _backend_name = "STAC"

    def __init__(
        self, url: str, minzoom: int, maxzoom: int, query: Dict = {}, **kwargs: Any
    ):
        """Initialize STACBackend."""
        self.path = url
        self.mosaic_def = self._read(query, minzoom, maxzoom, **kwargs)

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
        query: Dict,
        minzoom: int,
        maxzoom: int,
        accessor: Callable = default_stac_accessor,
        max_items: Optional[int] = None,
        stac_next_link_key: str = "next",
        **kwargs: Any
    ) -> MosaicJSON:
        """
        Fetch STAC API and construct the mosaicjson.

        Attributes
        ----------
        query : List, required
            List of GeoJSON features.
        minzoom: int, required
            Force mosaic min-zoom.
        maxzoom: int, required
            Force mosaic max-zoom.
        accessor: callable, required
            Function called on each feature to get its identifier.
        max_items: int, optional
            Limit the maximum of items returned by the API
        stac_next_link_key: str, optional (default: "next")
            link's 'next' key.
        kwargs: any
            Options forwarded to `MosaicJSON.from_features`

        Returns
        -------
        mosaic_definition : MosaicJSON
            Mosaic definition.

        """
        features = _fetch(
            self.path,
            json.dumps(query),
            max_items=max_items,
            next_link_key=stac_next_link_key,
        )

        return MosaicJSON.from_features(
            features, minzoom, maxzoom, accessor=accessor, **kwargs
        )


@functools.lru_cache(maxsize=512)
def _fetch(
    stac_url: str,
    query: str,
    max_items: Optional[int] = None,
    next_link_key: str = "next",
) -> List[Dict]:
    """Call STAC API."""
    features: List[Dict] = []

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Accept": "application/geo+json",
    }

    def _stac_search(url):
        return requests.post(url, headers=headers, data=query).json()

    next_url = stac_url
    while True:
        results = _stac_search(next_url)
        if not results.get("features"):
            break

        features.extend(results["features"])
        if max_items and len(features) >= max_items:
            break

        # https://github.com/radiantearth/stac-api-spec/blob/master/api-spec.md#paging-extension
        link = list(filter(lambda link: link["rel"] == next_link_key, results["links"]))
        if not link:
            break

        next_url = link[0]["href"]

    return features
