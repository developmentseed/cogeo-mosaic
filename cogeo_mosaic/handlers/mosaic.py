"""cogeo-mosaic.handlers.api_mosaic: handle request for cogeo-mosaic endpoints."""

from typing import Tuple

import json
import base64

import rasterio

from cogeo_mosaic.utils import create_mosaic, fetch_mosaic_definition, get_footprints

from lambda_proxy.proxy import API

app = API(name="cogeo-mosaic-mosaic")


@app.route(
    "/create",
    methods=["GET", "POST"],
    cors=True,
    payload_compression_method="gzip",
    binary_b64encode=True,
    tag=["mosaic"],
)
def _create_mosaic(body: str) -> Tuple[str, str, str]:
    body = json.loads(base64.b64decode(body).decode())
    return ("OK", "application/json", json.dumps(create_mosaic(body)))


@app.route(
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
        "name": url,
        "quadkeys": quadkeys,
        "layers": _get_layer_names(src_path),
    }
    return ("OK", "application/json", json.dumps(meta))


@app.route("/favicon.ico", methods=["GET"], cors=True, tag=["other"])
def favicon() -> Tuple[str, str, str]:
    """Favicon."""
    return ("EMPTY", "text/plain", "")
