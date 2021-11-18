"""cogeo-mosaic STAC backend."""

import json
import os
from typing import Dict, List, Optional, Sequence, Type

import attr
import httpx
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from rasterio.crs import CRS
from rio_tiler.constants import WGS84_CRS
from rio_tiler.io import STACReader

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError
from cogeo_mosaic.logger import logger
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


@attr.s
class STACBackend(BaseBackend):
    """STAC Backend Adapter

    Examples:
        >>> with STACBackend(
                "https://earth-search.aws.element84.com/v0/search",
                query,
                8,
                15,
            ) as mosaic:
                mosaic.tile(0, 0, 0)

    """

    input: str = attr.ib()
    query: Dict = attr.ib()

    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()

    reader: Type[STACReader] = attr.ib(default=STACReader)
    reader_options: Dict = attr.ib(factory=dict)

    # STAC API related options
    # max_items |  next_link_key | limit
    stac_api_options: Dict = attr.ib(factory=dict)

    # Mosaic Creation options
    # e.g `accessor`
    mosaic_options: Dict = attr.ib(factory=dict)

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    # Because the STACBackend is a Read-Only backend, there is no need for
    # mosaic_def to be in the init method.
    mosaic_def: MosaicJSON = attr.ib(init=False)

    _backend_name = "STAC"

    def __attrs_post_init__(self):
        """Post Init: if not passed in init, try to read from self.input."""
        self.mosaic_def = self._read()
        self.bounds = self.mosaic_def.bounds

    def _read(self) -> MosaicJSON:
        """
        Fetch STAC API and construct the mosaicjson.

        Returns:
            MosaicJSON: Mosaic definition.

        """
        logger.debug(f"Using STAC backend: {self.input}")

        features = _fetch(
            self.input,
            self.query,
            **self.stac_api_options,
        )
        logger.debug(f"Creating mosaic from {len(features)} features")

        # We need a specific accessor for STAC
        options = self.mosaic_options.copy()
        if "accessor" not in options:
            options["accessor"] = default_stac_accessor

        return MosaicJSON.from_features(features, self.minzoom, self.maxzoom, **options)

    def write(self, overwrite: bool = True):
        """Write mosaicjson document."""
        raise NotImplementedError

    def update(
        self,
        features: Sequence[Dict],
        add_first: bool = True,
        quiet: bool = False,
        **kwargs,
    ):
        """Update the mosaicjson document."""
        raise NotImplementedError


def query_from_link(link: Dict, query: Dict):
    """Handle Next Link."""
    q = query.copy()
    if link["method"] != "POST":
        raise MosaicError("Fetch doesn't support GET for next request.")

    if link.get("merge", False):
        q.update(link.get("body", {}))
    else:
        q = link.get("body", {})

    return q


@cached(
    TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
    key=lambda url, query, **kwargs: hashkey(url, json.dumps(query), **kwargs),
)
def _fetch(
    stac_url: str,
    query: Dict,
    max_items: Optional[int] = None,
    next_link_key: Optional[str] = None,
    limit: int = 500,
) -> List[Dict]:
    """Call STAC API."""
    features: List[Dict] = []
    stac_query = query.copy()

    headers = {
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
        "Accept": "application/geo+json",
    }

    if "limit" not in stac_query:
        stac_query.update({"limit": limit})

    def _stac_search(url: str, q: Dict):
        try:
            r = httpx.post(url, headers=headers, json=q)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            # post-flight errors
            status_code = e.response.status_code
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response.content) from e
        except httpx.RequestError as e:
            # pre-flight errors
            raise MosaicError(e.args[0].reason) from e
        return r.json()

    page = 1
    while True:
        logger.debug(f"Fetching page {page}")
        logger.debug("query: " + json.dumps(stac_query))

        results = _stac_search(stac_url, stac_query)
        if not results.get("features"):
            break

        features.extend(results["features"])
        if max_items and len(features) >= max_items:
            features = features[:max_items]
            break

        # new STAC context spec
        # {"page": 1, "limit": 1000, "matched": 5671, "returned": 1000}
        # SAT-API META
        # {"page": 4, "limit": 100, "found": 350, "returned": 50}
        ctx = results.get("context", results.get("meta"))
        matched = ctx.get("matched", ctx.get("found"))

        logger.debug(json.dumps(ctx))
        # Check if there is more data to fetch
        if matched <= ctx["returned"]:
            break

        # We shouldn't fetch more item than matched
        if len(features) == matched:
            break

        if len(features) > matched:
            raise MosaicError(
                "Something weird is going on, please open an issue in https://github.com/developmentseed/cogeo-mosaic"
            )
        page += 1

        # https://github.com/radiantearth/stac-api-spec/blob/master/api-spec.md#paging-extension
        if next_link_key:
            links = list(
                filter(lambda link: link["rel"] == next_link_key, results["links"])
            )
            if not links:
                break
            stac_query = query_from_link(links[0], stac_query)
        else:
            stac_query.update({"page": page})

    return features
