"""cogeo-mosaic.handlers.api_tiles: handle request for cogeo-mosaic endpoints."""

from typing import Any, Tuple, Union

import os
import json
import urllib

import numpy

import mercantile

import rasterio
from rasterio.transform import from_bounds

from rio_color.utils import scale_dtype, to_math_type
from rio_color.operations import parse_operations

from rio_tiler.main import tile as cogeoTiler
from rio_tiler.utils import array_to_image, get_colormap, linear_rescale
from rio_tiler.profiles import img_profiles

from rio_tiler_mvt.mvt import encoder as mvtEncoder
from rio_tiler_mosaic.mosaic import mosaic_tiler
from rio_tiler_mosaic.methods import defaults

from cogeo_mosaic import custom_methods
from cogeo_mosaic.custom_cmaps import get_custom_cmap
from cogeo_mosaic.ogc import wmts_template
from cogeo_mosaic.utils import (
    fetch_mosaic_definition,
    fetch_and_find_assets,
    fetch_and_find_assets_point,
    get_point_values,
    _create_path,
)

from lambda_proxy.proxy import API

PIXSEL_METHODS = {
    "first": defaults.FirstMethod,
    "highest": defaults.HighestMethod,
    "lowest": defaults.LowestMethod,
    "mean": defaults.MeanMethod,
    "median": defaults.MedianMethod,
    "stdev": defaults.StdevMethod,
    "bdix_stdev": custom_methods.bidx_stddev,
}
app = API(name="cogeo-mosaic-tiles")


@app.route(
    "/tilejson.json",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/tilejson.json",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
def _get_tilejson(
    mosaicid: str = None,
    url: str = None,
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

    kwargs.update(dict(url=url))
    qs = urllib.parse.urlencode(list(kwargs.items()))
    if tile_format in ["pbf", "mvt"]:
        tile_url = f"{app.host}/tiles/{{z}}/{{x}}/{{y}}.{tile_format}?{qs}"
    else:
        tile_url = (
            f"{app.host}/tiles/{{z}}/{{x}}/{{y}}@{tile_scale}x.{tile_format}?{qs}"
        )

    meta = {
        "bounds": bounds,
        "center": center,
        "maxzoom": mosaic_def["maxzoom"],
        "minzoom": mosaic_def["minzoom"],
        "name": url,
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


@app.route(
    "/wmts",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["OGC"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/wmts",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["metadata"],
)
def _get_mosaic_wmts(
    mosaicid: str = None,
    url: str = None,
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
    if mosaicid:
        url = _create_path(mosaicid)
    elif url is None:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    if tile_scale is not None and isinstance(tile_scale, str):
        tile_scale = int(tile_scale)

    mosaic_def = fetch_mosaic_definition(url)

    kwargs.pop("SERVICE", None)
    kwargs.pop("REQUEST", None)
    kwargs.update(dict(url=url))
    query_string = urllib.parse.urlencode(list(kwargs.items()))
    query_string = query_string.replace(
        "&", "&amp;"
    )  # & is an invalid character in XML

    return (
        "OK",
        "application/xml",
        wmts_template(
            f"{app.host}/tiles",
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


@app.route(
    "/<int:z>/<int:x>/<int:y>.pbf",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/<int:z>/<int:x>/<int:y>.pbf",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
def mosaic_mvt(
    mosaicid: str = None,
    z: int = None,
    x: int = None,
    y: int = None,
    url: str = None,
    tile_size: Union[str, int] = 256,
    pixel_selection: str = "first",
    feature_type: str = "point",
    resampling_method: str = "nearest",
):
    """Handle MVT requests."""
    if mosaicid:
        url = _create_path(mosaicid)
    elif url is None:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    assets = fetch_and_find_assets(url, x, y, z)
    if not assets:
        return ("EMPTY", "text/plain", f"No assets found for tile {z}-{x}-{y}")

    if tile_size is not None and isinstance(tile_size, str):
        tile_size = int(tile_size)

    pixsel_method = PIXSEL_METHODS[pixel_selection]
    tile, mask = mosaic_tiler(
        assets,
        x,
        y,
        z,
        cogeoTiler,
        tilesize=tile_size,
        pixel_selection=pixsel_method(),
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


@app.route(
    "/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@app.route(
    "/<int:z>/<int:x>/<int:y>@<int:scale>x.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/<int:z>/<int:x>/<int:y>.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/<int:z>/<int:x>/<int:y>@<int:scale>x.<ext>",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
def mosaic_img(
    mosaicid: str = None,
    z: int = None,
    x: int = None,
    y: int = None,
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
    if mosaicid:
        url = _create_path(mosaicid)
    elif url is None:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    assets = fetch_and_find_assets(url, x, y, z)
    if not assets:
        return ("EMPTY", "text/plain", f"No assets found for tile {z}-{x}-{y}")

    if indexes:
        indexes = list(map(int, indexes.split(",")))

    tilesize = 256 * scale

    pixsel_method = PIXSEL_METHODS[pixel_selection]
    tile, mask = mosaic_tiler(
        assets,
        x,
        y,
        z,
        cogeoTiler,
        indexes=indexes,
        tilesize=tilesize,
        pixel_selection=pixsel_method(),
        resampling_method=resampling_method,
    )

    if tile is None:
        return ("EMPTY", "text/plain", "empty tiles")

    rtile = _postprocess(tile, mask, rescale=rescale, color_formula=color_ops)
    if color_map:
        if color_map.startswith("custom_"):
            color_map = get_custom_cmap(color_map)
        else:
            color_map = get_colormap(color_map, format="gdal")

    driver = "jpeg" if ext == "jpg" else ext
    options = img_profiles.get(driver, {})

    if ext == "tif":
        ext = "tiff"
        driver = "GTiff"
        tile_bounds = mercantile.xy_bounds(mercantile.Tile(x=x, y=y, z=z))
        options = dict(
            crs={"init": "EPSG:3857"},
            transform=from_bounds(*tile_bounds, tilesize, tilesize),
        )

    return (
        "OK",
        f"image/{ext}",
        array_to_image(rtile, mask, img_format=driver, color_map=color_map, **options),
    )


@app.route(
    "/point",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
@app.route(
    "/<regex([0-9A-Fa-f]{56}):mosaicid>/point",
    methods=["GET"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["tiles"],
)
def mosaic_point(
    mosaicid: str = None, lng: float = None, lat: float = None, url: str = None
):
    """Handle point requests."""
    if mosaicid:
        url = _create_path(mosaicid)
    elif url is None:
        return ("NOK", "text/plain", "Missing 'URL' parameter")

    if not lat or not lng:
        return ("NOK", "text/plain", "Missing 'Lon/Lat' parameter")

    if isinstance(lng, str):
        lng = float(lng)

    if isinstance(lat, str):
        lat = float(lat)

    assets = fetch_and_find_assets_point(url, lng, lat)
    if not assets:
        return ("EMPTY", "text/plain", f"No assets found for lat/lng ({lat}, {lng})")

    meta = {"coordinates": [lng, lat], "values": get_point_values(assets, lng, lat)}
    return ("OK", "application/json", json.dumps(meta))


@app.route("/favicon.ico", methods=["GET"], cors=True, tag=["other"])
def favicon() -> Tuple[str, str, str]:
    """Favicon."""
    return ("EMPTY", "text/plain", "")
