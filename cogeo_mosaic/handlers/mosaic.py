"""cogeo-mosaic.handlers.api_mosaic: handle request for cogeo-mosaic endpoints."""

from typing import Any, Tuple, Union

import os
import json
import urllib

from botocore.errorfactory import ClientError

import rasterio

from cogeo_mosaic.utils import (
    create_mosaic,
    fetch_mosaic_definition,
    get_footprints,
    get_hash,
    _aws_put_data,
    _compress_gz_json,
    _create_path,
)
from cogeo_mosaic import version as mosaic_version

from lambda_proxy.proxy import API

app = API(name="cogeo-mosaic-mosaic", debug=True)


@app.route(
    "/create",
    methods=["GET", "POST"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["mosaic"],
)
def _create_mosaic(
    body: str,
    minzoom: Union[str, int] = None,
    maxzoom: Union[str, int] = None,
    min_tile_cover: Union[str, float] = None,
    tile_cover_sort: Union[str, bool] = False,
    tile_format: str = "png",
    tile_scale: Union[str, int] = 1,
    **kwargs: Any,
) -> Tuple[str, str, str]:
    minzoom = int(minzoom) if isinstance(minzoom, str) else minzoom
    maxzoom = int(maxzoom) if isinstance(maxzoom, str) else maxzoom
    min_tile_cover = (
        float(min_tile_cover) if isinstance(min_tile_cover, float) else min_tile_cover
    )

    mosaicid = get_hash(body=body, version=mosaic_version)

    try:
        mosaic_definition = fetch_mosaic_definition(_create_path(mosaicid))
    except ClientError:
        body = json.loads(body)
        mosaic_definition = create_mosaic(
            body,
            minzoom=minzoom,
            maxzoom=maxzoom,
            minimum_tile_cover=min_tile_cover,
            tile_cover_sort=tile_cover_sort,
        )

        key = f"mosaics/{mosaicid}.json.gz"
        bucket = os.environ["MOSAIC_DEF_BUCKET"]
        _aws_put_data(key, bucket, _compress_gz_json(mosaic_definition))

    qs = urllib.parse.urlencode(list(kwargs.items()))
    tile_url = (
        f"{app.host}/tiles/{mosaicid}/{{z}}/{{x}}/{{y}}@{tile_scale}x.{tile_format}"
    )
    if qs:
        tile_url += f"?{qs}"

    meta = {
        "bounds": mosaic_definition["bounds"],
        "center": mosaic_definition["center"],
        "maxzoom": mosaic_definition["maxzoom"],
        "minzoom": mosaic_definition["minzoom"],
        "name": mosaicid,
        "tilejson": "2.1.0",
        "tiles": [tile_url],
    }

    return ("OK", "application/json", json.dumps(meta))


@app.route(
    "/footprint",
    methods=["GET", "POST"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["mosaic"],
)
def _create_footpring(body: str) -> Tuple[str, str, str]:
    mosaicid = get_hash(body=body, version=mosaic_version)
    key = f"mosaics/{mosaicid}.geojson"
    bucket = os.environ["MOSAIC_DEF_BUCKET"]

    try:
        geojson = fetch_mosaic_definition(f"s3://{bucket}/{key}")  # HACK
    except ClientError:
        body = json.loads(body)
        geojson = {"features": get_footprints(body), "type": "FeatureCollection"}
        _aws_put_data(key, bucket, json.dumps(geojson).encode("utf-8"))

    return ("OK", "application/json", json.dumps(geojson))


def _get_layer_names(src_path):
    with rasterio.open(src_path) as src_dst:

        def _get_name(ix):
            name = src_dst.descriptions[ix - 1]
            if not name:
                name = f"band{ix}"
            return name

        return [_get_name(ix) for ix in src_dst.indexes]


@app.route(
    "/info",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
@app.route(
    "/info/<regex([0-9A-Fa-f]{56}):mosaicid>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
def _get_mosaic_info(mosaicid: str = None, url: str = None) -> Tuple[str, str, str]:
    """
    Handle /info requests.

    Attributes
    ----------
    url : str, required
        Mosaic definition url.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/json).
    body : str
        String encoded JSON metata

    """
    if mosaicid:
        url = _create_path(mosaicid)
    elif url is None:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    mosaic_def = fetch_mosaic_definition(url)

    bounds = mosaic_def["bounds"]
    center = [
        (bounds[0] + bounds[2]) / 2,
        (bounds[1] + bounds[3]) / 2,
        mosaic_def["minzoom"],
    ]
    quadkeys = list(mosaic_def["tiles"].keys())

    # read layernames from the first file
    src_path = mosaic_def["tiles"][quadkeys[0]][0]

    meta = {
        "bounds": bounds,
        "center": center,
        "maxzoom": mosaic_def["maxzoom"],
        "minzoom": mosaic_def["minzoom"],
        "name": url,
        "quadkeys": quadkeys,
        "layers": _get_layer_names(src_path),
    }
    return ("OK", "application/json", json.dumps(meta))


@app.route("/favicon.ico", methods=["GET"], cors=True, tag=["other"])
def favicon() -> Tuple[str, str, str]:
    """Favicon."""
    return ("EMPTY", "text/plain", "")
