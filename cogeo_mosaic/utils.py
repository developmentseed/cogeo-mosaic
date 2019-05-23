"""cogeo_mosaic.utils: utility functions."""

from typing import Dict, Tuple
from typing.io import BinaryIO

import os
import zlib
import json
import warnings
import functools
import itertools
from concurrent import futures
from urllib.parse import urlparse

import requests

import mercantile
from shapely.geometry import shape, box
from shapely.ops import cascaded_union
from supermercado import burntiles, uniontiles

import rasterio
from rio_tiler.mercator import get_zooms
from rasterio.warp import transform_bounds

from boto3.session import Session as boto3_session


def _decompress_gz(gzip_buffer):
    return zlib.decompress(gzip_buffer, zlib.MAX_WBITS | 16).decode()


def _compress_gz_json(data):
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    return (
        gzip_compress.compress(json.dumps(data).encode("utf-8")) + gzip_compress.flush()
    )


def _aws_put_data(key: str, bucket: str, body: BinaryIO, options: Dict = {}) -> str:
    session = boto3_session()
    s3 = session.client("s3")
    s3.put_object(Bucket=bucket, Key=key, Body=body, **options)
    return key


def _aws_get_data(key, bucket):
    session = boto3_session()
    s3 = session.client("s3")

    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def get_dataset_info(src_path: str) -> Dict:
    """Get rasterio dataset meta."""
    with rasterio.open(src_path) as src_dst:
        bounds = transform_bounds(
            *[src_dst.crs, "epsg:4326"] + list(src_dst.bounds), densify_pts=21
        )
        min_zoom, max_zoom = get_zooms(src_dst, ensure_global_max_zoom=True)
        return {
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [bounds[0], bounds[3]],
                        [bounds[0], bounds[1]],
                        [bounds[2], bounds[1]],
                        [bounds[2], bounds[3]],
                        [bounds[0], bounds[3]],
                    ]
                ],
            },
            "properties": {
                "path": src_path,
                "bounds": bounds,
                "minzoom": min_zoom,
                "maxzoom": max_zoom,
                "datatype": src_dst.meta["dtype"],
            },
            "type": "Feature",
        }


def create_mosaic(
    dataset_list: Tuple, max_threads: int = 20, version: str = "0.0.1"
) -> Dict:
    """
    Create mosaic definition content.


    Attributes
    ----------
    dataset_listurl : tuple or list, required
        Dataset urls.
    max_threads : int
        Image format to return (default: png).
    version: str, optional
        mosaicJSON definition version

    Returns
    -------
    mosaic_definition : dict
        Mosaic definition.

    """
    with futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        results = list(executor.map(get_dataset_info, dataset_list))

    checks = [
        (
            feat["properties"]["minzoom"],
            feat["properties"]["maxzoom"],
            feat["properties"]["datatype"],
        )
        for feat in filter(None, results)
    ]

    minzoom = list(set([z[0] for z in checks]))
    maxzoom = list(set([z[1] for z in checks]))

    if len(maxzoom) > 1:
        warnings.warn(
            "Multiple MaxZoom, Assets have multiple resolution values", UserWarning
        )

    if len(minzoom) > 1:
        warnings.warn(
            "Multiple MinZoom, Assets different minzoom values", UserWarning
        )

    data_types = list(set([z[2] for z in checks]))
    if len(data_types) > 1:
        raise Exception("Dataset should have the same data type")

    tiles = burntiles.burn(results, max(minzoom))
    tiles = ["{2}-{0}-{1}".format(*tile.tolist()) for tile in tiles]

    collection = cascaded_union(
        [shape(f["geometry"]) for f in uniontiles.union(tiles, True)]
    )
    if version == "0.0.1":
        mosaic_definition = dict(
            minzoom=max(minzoom),
            maxzoom=max(maxzoom),
            bounds=list(collection.bounds),
            center=[collection.centroid.x, collection.centroid.y],
            tiles={},
        )

        dataset = [
            {"path": f["properties"]["path"], "geometry": shape(f["geometry"])}
            for f in filter(None, results)
        ]

        for parent in tiles:
            z, x, y = list(map(int, parent.split("-")))
            parent = mercantile.Tile(x=x, y=y, z=z)
            quad = mercantile.quadkey(*parent)
            tile_geometry = box(*mercantile.bounds(parent))
            fdataset = list(filter(
                lambda x: tile_geometry.intersects(x["geometry"]), dataset
            ))
            if len(fdataset):
                mosaic_definition["tiles"][quad] = [f["path"] for f in fdataset]
    else:
        raise Exception(f"Invalid mosaicJSON version: {version}")

    return mosaic_definition


def get_mosaic_content(url: str) -> Dict:
    """Get Mosaic document."""
    url_info = urlparse(url)

    if url_info.scheme == "s3":
        bucket = url_info.netloc
        key = url_info.path.strip("/")
        body = _aws_get_data(key, bucket)

    elif url_info.scheme in ["http", "https"]:
        # use requests
        body = requests.get(url)
        body = body.content

    else:
        with open(url, "rb") as f:
            body = f.read()

    if url.endswith(".gz"):
        body = _decompress_gz(body)

    if isinstance(body, dict):
        return body
    else:
        return json.loads(body)


@functools.lru_cache(maxsize=512)
def fetch_mosaic_definition(url: str) -> Dict:
    """Get Mosaic definition info."""
    return get_mosaic_content(url)


def get_assets(url: str, x: int, y: int, z: int) -> Tuple[str]:
    """Get assets."""
    mosaic_def = fetch_mosaic_definition(url)
    min_zoom = mosaic_def["minzoom"]
    max_zoom = mosaic_def["maxzoom"]
    if z > max_zoom or z < min_zoom:
        return []  # return empty asset

    mercator_tile = mercantile.Tile(x=x, y=y, z=z)
    quadkey_zoom = mosaic_def.get("quadkey_zoom", min_zoom)  # 0.0.2

    # get parent
    if mercator_tile.z > quadkey_zoom:
        depth = mercator_tile.z - quadkey_zoom
        for i in range(depth):
            mercator_tile = mercantile.parent(mercator_tile)
        quadkey = [mercantile.quadkey(*mercator_tile)]

    # get child
    elif mercator_tile.z < quadkey_zoom:
        depth = quadkey_zoom - mercator_tile.z
        mercator_tiles = [mercator_tile]
        for i in range(depth):
            mercator_tiles = sum([mercantile.children(t) for t in mercator_tiles], [])

        mercator_tiles = list(filter(lambda t: t.z == quadkey_zoom, mercator_tiles))
        quadkey = [mercantile.quadkey(*tile) for tile in mercator_tiles]

    else:
        quadkey = [mercantile.quadkey(*mercator_tile)]

    assets = list(
        itertools.chain.from_iterable([mosaic_def["tiles"].get(qk) for qk in quadkey])
    )

    # check if we have a mosaic in the url (.json/.gz)
    return list(
        itertools.chain.from_iterable(
            [
                get_assets(asset, x, y, z)
                if os.path.splitext(asset)[1] in [".json", ".gz"]
                else [asset]
                for asset in assets
            ]
        )
    )
