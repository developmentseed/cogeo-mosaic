"""cogeo-mosaic STAC backend."""

import json
import os
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse

import mercantile
import requests
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import get_assets_from_json
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError
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
    """
    STAC Backend Adapter

    Usage:
    ------
    with STACBackend(
        "https://earth-search.aws.element84.com/v0/search",
        query,
        8,
        15,
    ) as mosaic:
        mosaic.tile(0, 0, 0)

    """

    _backend_name = "STAC"

    def __init__(
        self, url: str, query: Dict, minzoom: int, maxzoom: int, **kwargs: Any
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
        stac_query_limit: int = 500,
        stac_next_link_key: str = "next",
        **kwargs: Any
    ) -> MosaicJSON:
        """
        Fetch STAC API and construct the mosaicjson.

        Attributes
        ----------
        query : Dict, required
            STAC API POST request query.
        minzoom: int, required
            mosaic min-zoom.
        maxzoom: int, required
            mosaic max-zoom.
        accessor: callable, required
            Function called on each feature to get its identifier.
        max_items: int, optional
            Limit the maximum of items returned by the API
        stac_query_limit: int, optional
            Add "limit" option to the POST Query, default is set to 500.
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
            query,
            max_items=max_items,
            limit=stac_query_limit,
            next_link_key=stac_next_link_key,
        )

        return MosaicJSON.from_features(
            features, minzoom, maxzoom, accessor=accessor, **kwargs
        )


@cached(
    TTLCache(maxsize=512, ttl=300),
    key=lambda url, query, **kwargs: hashkey(url, json.dumps(query), **kwargs),
)
def _fetch(
    stac_url: str,
    query: Dict,
    max_items: Optional[int] = None,
    next_link_key: str = "next",
    limit: int = 500,
) -> List[Dict]:
    """Call STAC API."""
    features: List[Dict] = []

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Accept": "application/geo+json",
    }

    if "features" not in query:
        query.update({"limit": limit})

    def _stac_search(url):
        try:
            r = requests.post(url, headers=headers, json=query)
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # post-flight errors
            status_code = e.response.status_code
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response.content) from e
        except requests.exceptions.RequestException as e:
            # pre-flight errors
            raise MosaicError(e.args[0].reason) from e
        return r.json()

    next_url = stac_url
    page = 1
    while True:
        # HACK: next token is not yet handled in some API
        parsed_url = urlparse(next_url)
        qs: Dict[str, Any] = dict(parse_qsl(parsed_url.query))
        qs.update({"page": page})
        updated_query = urlencode(qs)
        next_url = parsed_url._replace(query=updated_query).geturl()

        results = _stac_search(next_url)
        if not results.get("features"):
            break

        features.extend(results["features"])
        if max_items and len(features) >= max_items:
            features = features[:max_items]
            break

        # Check if there is more data to fetch
        if results["context"]["matched"] <= results["context"]["returned"]:
            break

        # Right now we construct the next URL
        # https://github.com/radiantearth/stac-api-spec/blob/master/api-spec.md#paging-extension
        # link = list(filter(lambda link: link["rel"] == next_link_key, results["links"]))
        # if not link:
        #     break
        # next_url = link[0]["href"]

        page += 1

    return features
