"""cogeo-mosaic STAC backend."""

import json
import os
from typing import Any, Callable, Dict, List, Optional, Type

import attr
import requests
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
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

    path: str = attr.ib()
    query: Dict = attr.ib()
    minzoom: int = attr.ib()
    maxzoom: int = attr.ib()
    mosaic_def: MosaicJSON = attr.ib(default=None)
    reader: Type[STACReader] = attr.ib(default=STACReader)
    reader_options: Dict = attr.ib(factory=dict)
    backend_options: Dict = attr.ib(factory=dict)

    _backend_name = "STAC"

    def __attrs_post_init__(self):
        """Post Init: if not passed in init, try to read from self.path."""
        self.mosaic_def = self.mosaic_def or self._read(
            self.query, self.minzoom, self.maxzoom, **self.backend_options
        )
        self.bounds = self.mosaic_def.bounds

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
        stac_next_link_key: Optional[str] = None,
        **kwargs: Any,
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
        stac_next_link_key: str, optional
            link's 'next' key.
        kwargs: any
            Options forwarded to `MosaicJSON.from_features`

        Returns
        -------
        mosaic_definition : MosaicJSON
            Mosaic definition.

        """
        logger.debug(f"Using STAC backend: {self.path}")

        features = _fetch(
            self.path,
            query,
            max_items=max_items,
            limit=stac_query_limit,
            next_link_key=stac_next_link_key,
        )
        logger.debug(f"Creating mosaic from {len(features)} features")

        return MosaicJSON.from_features(
            features, minzoom, maxzoom, accessor=accessor, **kwargs
        )


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
            r = requests.post(url, headers=headers, json=q)
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
