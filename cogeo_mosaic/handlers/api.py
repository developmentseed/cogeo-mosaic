"""cogeo-mosaic.handlers.api: handle request for cogeo-mosaic endpoints."""

from typing import Any, Tuple, Union

import os
import json
import base64
import urllib

import numpy
import rasterio

from rio_color.utils import scale_dtype, to_math_type
from rio_color.operations import parse_operations

from rio_tiler.main import tile as cogeoTiler
from rio_tiler.utils import array_to_image, get_colormap, linear_rescale
from rio_tiler.profiles import img_profiles

from rio_tiler_mvt.mvt import encoder as mvtEncoder
from rio_tiler_mosaic.mosaic import mosaic_tiler

from cogeo_mosaic.ogc import wmts_template
from cogeo_mosaic.utils import (
    create_mosaic,
    fetch_mosaic_definition,
    get_assets,
    get_footprints,
)

from lambda_proxy.proxy import API

APP = API(name="cogeo-mosaic")


@APP.route(
    "/footprint",
    methods=["GET", "POST"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["mosaic"],
)
def _create_footpring(body: str) -> Tuple[str, str, str]:
    body = json.loads(base64.b64decode(body).decode())
    return (
        "OK",
        "application/json",
        json.dumps({"features": get_footprints(body), "type": "FeatureCollection"}),
    )


@APP.route(
    "/mosaic",
    methods=["GET", "POST"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["mosaic"],
)
def _create_mosaic(body: str) -> Tuple[str, str, str]:
    body = json.loads(base64.b64decode(body).decode())
    return ("OK", "application/json", json.dumps(create_mosaic(body)))


@APP.route(
    "/tilejson.json",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
@APP.pass_event
def _get_tilejson(
    request: dict,
    url: str,
    tile_format: str = "png",
    tile_scale: int = 1,
    **kwargs: Any,
) -> Tuple[str, str, str]:
    """
    Handle /tilejson.json requests.

    Note: All the querystring parameters are translated to function keywords
    and passed as string value by lambda_proxy

    Attributes
    ----------
    url : str, required
        Mosaic definition.
    tile_format : str
        Image format to return (default: png).
    tile_scale : int, optional
        Tile image scale (default: 1).
    kwargs: dict, optional
        Querystring parameters to forward to the tile url.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/json).
    body : str
        String encoded tileJSON

    """
    mosaic_def = fetch_mosaic_definition(url)

    bounds = mosaic_def["bounds"]
    center = [
        (bounds[0] + bounds[2]) / 2,
        (bounds[1] + bounds[3]) / 2,
        mosaic_def["minzoom"],
    ]

    host = request["headers"].get(
        "X-Forwarded-Host", request["headers"].get("Host", "")
    )
    # Check for API gateway stage
    if ".execute-api." in host and ".amazonaws.com" in host:
        stage = request["requestContext"].get("stage", "")
        host = f"{host}/{stage}"

    scheme = "http" if host.startswith("127.0.0.1") else "https"

    kwargs.update(dict(url=url))
    qs = urllib.parse.urlencode(list(kwargs.items()))

    if tile_format in ["pbf", "mvt"]:
        tile_url = f"{scheme}://{host}/{{z}}/{{x}}/{{y}}.{tile_format}?{qs}"
    else:
        tile_url = (
            f"{scheme}://{host}/{{z}}/{{x}}/{{y}}@{tile_scale}x.{tile_format}?{qs}"
        )

    meta = {
        "bounds": bounds,
        "center": center,
        "maxzoom": mosaic_def["maxzoom"],
        "minzoom": mosaic_def["minzoom"],
        "name": os.path.basename(url),
        "tilejson": "2.1.0",
        "tiles": [tile_url],
    }
    return ("OK", "application/json", json.dumps(meta))


def _get_layer_names(src_path):
    with rasterio.open(src_path) as src_dst:

        def _get_name(ix):
            name = src_dst.descriptions[ix - 1]
            if not name:
                name = f"band{ix}"
            return name

        return [_get_name(ix) for ix in src_dst.indexes]


@APP.route(
    "/info",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
def _get_mosaic_info(url: str) -> Tuple[str, str, str]:
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
        "name": os.path.basename(url),
        "quadkeys": quadkeys,
        "layers": _get_layer_names(src_path),
    }
    return ("OK", "application/json", json.dumps(meta))


@APP.route(
    "/wmts",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["OGC"],
)
@APP.pass_event
def _get_mosaic_wmts(
    request: dict,
    url: str,
    tile_format: str = "png",
    tile_scale: int = 1,
    title: str = "Cloud Optimizied GeoTIFF Mosaic",
    **kwargs: Any,
) -> Tuple[str, str, str]:
    """
    Handle /wmts requests.

    Attributes
    ----------
    url : str, required
        Mosaic definition url.
    tile_format : str
        Image format to return (default: png).
    tile_scale : int, optional
        Tile image scale (default: 1).
    kwargs: dict, optional
        Querystring parameters to forward to the tile url.

    Returns
    -------
    status : str
        Status of the request (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. application/json).
    body : str
        String encoded JSON metata

    """
    if tile_scale is not None and isinstance(tile_scale, str):
        tile_scale = int(tile_scale)

    mosaic_def = fetch_mosaic_definition(url)

    host = request["headers"].get(
        "X-Forwarded-Host", request["headers"].get("Host", "")
    )
    # Check for API gateway stage
    if ".execute-api." in host and ".amazonaws.com" in host:
        stage = request["requestContext"].get("stage", "")
        host = f"{host}/{stage}"

    scheme = "http" if host.startswith("127.0.0.1") else "https"

    kwargs.pop("SERVICE", None)
    kwargs.pop("REQUEST", None)
    kwargs.update(dict(url=url))
    query_string = urllib.parse.urlencode(list(kwargs.items()))
    query_string = query_string.replace(
        "&", "&amp;"
    )  # & is an invalid character in XML
    endpoint = f"{scheme}://{host}"

    return (
        "OK",
        "application/xml",
        wmts_template(
            endpoint,
            os.path.basename(url),
            query_string,
            minzoom=mosaic_def["minzoom"],
            maxzoom=mosaic_def["maxzoom"],
            bounds=mosaic_def["bounds"],
            tile_scale=tile_scale,
            tile_format=tile_format,
            title=title,
        ),
    )


@APP.route(
    "/<int:z>/<int:x>/<int:y>.pbf",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@APP.route(
    "/<int:z>/<int:x>/<int:y>.mvt",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
def mosaic_mvt(
    z: int,
    x: int,
    y: int,
    url: str,
    tile_size: Union[str, int] = 256,
    pixel_selection: str = "first",
    feature_type: str = "point",
    resampling_method: str = "nearest",
):
    """Handle MVT requests."""
    assets = get_assets(url, x, y, z)
    if not assets:
        return ("EMPTY", "text/plain", f"No assets found for tile {z}-{x}-{y}")

    if tile_size is not None and isinstance(tile_size, str):
        tile_size = int(tile_size)

    tile, mask = mosaic_tiler(
        assets,
        x,
        y,
        z,
        cogeoTiler,
        tilesize=tile_size,
        pixel_selection=pixel_selection,
        resampling_method=resampling_method,
    )
    if tile is None:
        return ("EMPTY", "text/plain", "empty tiles")

    band_descriptions = _get_layer_names(assets[0])
    return (
        "OK",
        "application/x-protobuf",
        mvtEncoder(
            tile,
            mask,
            band_descriptions,
            os.path.basename(url),
            feature_type=feature_type,
        ),
    )


def _postprocess(
    tile: numpy.ndarray,
    mask: numpy.ndarray,
    rescale: str = None,
    color_formula: str = None,
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    """Tile data post processing."""
    if rescale:
        rescale_arr = (tuple(map(float, rescale.split(","))),) * tile.shape[0]
        for bdx in range(tile.shape[0]):
            tile[bdx] = numpy.where(
                mask,
                linear_rescale(
                    tile[bdx], in_range=rescale_arr[bdx], out_range=[0, 255]
                ),
                0,
            )
        tile = tile.astype(numpy.uint8)

    if color_formula:
        # make sure one last time we don't have
        # negative value before applying color formula
        tile[tile < 0] = 0
        for ops in parse_operations(color_formula):
            tile = scale_dtype(ops(to_math_type(tile)), numpy.uint8)

    return tile


@APP.route(
    "/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@APP.route(
    "/<int:z>/<int:x>/<int:y>@<int:scale>x.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
def mosaic_img(
    z: int,
    x: int,
    y: int,
    scale: int = 1,
    ext: str = "png",
    url: str = None,
    indexes: str = None,
    rescale: str = None,
    color_ops: str = None,
    color_map: str = None,
    pixel_selection: str = "first",
    resampling_method: str = "nearest",
):
    """Handle tile requests."""
    if not url:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    assets = get_assets(url, x, y, z)
    if not assets:
        return ("EMPTY", "text/plain", f"No assets found for tile {z}-{x}-{y}")

    if indexes:
        indexes = list(map(int, indexes.split(",")))

    tilesize = 256 * scale
    tile, mask = mosaic_tiler(
        assets,
        x,
        y,
        z,
        cogeoTiler,
        indexes=indexes,
        tilesize=tilesize,
        pixel_selection=pixel_selection,
        resampling_method=resampling_method,
    )

    if tile is None:
        return ("EMPTY", "text/plain", "empty tiles")

    rtile = _postprocess(tile, mask, rescale=rescale, color_formula=color_ops)
    if color_map:
        color_map = get_colormap(color_map, format="gdal")

    driver = "jpeg" if ext == "jpg" else ext
    options = img_profiles.get(driver, {})
    return (
        "OK",
        f"image/{ext}",
        array_to_image(rtile, mask, img_format=driver, color_map=color_map, **options),
    )


@APP.route("/favicon.ico", methods=["GET"], cors=True, tag=["other"])
def favicon() -> Tuple[str, str, str]:
    """Favicon."""
    return ("EMPTY", "text/plain", "")
