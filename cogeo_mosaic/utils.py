"""cogeo_mosaic.utils: utility functions."""

from typing import Dict, Tuple, BinaryIO

import os
import sys
import zlib
import json
import hashlib
import warnings
import functools
import itertools
from concurrent import futures
from urllib.parse import urlparse

import click
import requests

import mercantile
from shapely.geometry import shape, box
from supermercado import burntiles

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


def get_hash(**kwargs: Dict) -> str:
    """Create hash from a dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()
    ).hexdigest()


def _create_path(mosaicid: str) -> str:
    """Get Mosaic definition info."""
    key = f"mosaics/{mosaicid}.json.gz"
    bucket = os.environ["MOSAIC_DEF_BUCKET"]
    return f"s3://{bucket}/{key}"


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


def get_footprints(
    dataset_list: Tuple, max_threads: int = 20, quiet: bool = True
) -> Tuple:
    """
    Create footprint GeoJSON.

    Attributes
    ----------
    dataset_listurl : tuple or list, required
        Dataset urls.
    max_threads : int
        Max threads to use (default: 20).

    Returns
    -------
    out : tuple
        tuple of footprint feature.

    """
    fout = os.devnull if quiet else sys.stderr
    with futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_work = [executor.submit(get_dataset_info, item) for item in dataset_list]
        with click.progressbar(
            futures.as_completed(future_work),
            file=fout,
            length=len(future_work),
            show_percent=True,
        ) as future:
            for res in future:
                pass

    return [future.result() for future in future_work]


def _tiles_bounds(features, zoom):
    """Return bounding box for bounding tiles."""
    bounds = burntiles.find_extrema(features)
    extrema = burntiles.tile_extrema(bounds, zoom)
    ulx, uly = mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], zoom)
    lrx, lry = mercantile.ul(extrema["x"]["max"], extrema["y"]["max"], zoom)
    return [ulx, lry, lrx, uly]


def _intersect_percent(tile, geom):
    """Return the overlap percent."""
    inter = tile.intersection(geom)
    return inter.area / tile.area if inter else 0.0


def _filter_and_sort(tile, dataset, minimum_cover=0.0, sort_cover=False):
    """Filter and/or sort dataset per intersection coverage."""
    dataset = [(_intersect_percent(tile, x["geometry"]), x) for x in dataset]

    if minimum_cover:
        dataset = list(filter(lambda x: x[0] > minimum_cover, dataset))

    if sort_cover:
        dataset = sorted(dataset, key=lambda x: x[0], reverse=True)

    return [x[1] for x in dataset]


def create_mosaic(
    dataset_list: Tuple,
    minzoom: int = None,
    maxzoom: int = None,
    max_threads: int = 20,
    minimum_tile_cover: float = 0.0,
    tile_cover_sort: bool = False,
    version: str = "0.0.1",
    quiet: bool = True,
) -> Dict:
    """
    Create mosaic definition content.

    Attributes
    ----------
    dataset_list : tuple or list, required
        Dataset urls.
    minzoom: int, optional
        Force mosaic min-zoom.
    maxzoom: int, optional
        Force mosaic max-zoom.
    minimum_tile_cover: float, optional (default: 0)
        Filter files with low tile intersection coverage.
    tile_cover_sort: bool, optional (default: None)
        Sort intersecting files by coverage.
    max_threads : int
        Max threads to use (default: 20).
    version: str, optional
        mosaicJSON definition version
    quiet: bool, optional (default: True)
        Mask processing steps.

    Returns
    -------
    mosaic_definition : dict
        Mosaic definition.

    """
    if not quiet:
        click.echo("Get files footprint", err=True)
    results = get_footprints(dataset_list, max_threads=max_threads, quiet=quiet)

    if minzoom is None:
        minzoom = list(set([feat["properties"]["minzoom"] for feat in results]))
        if len(minzoom) > 1:
            warnings.warn(
                "Multiple MinZoom, Assets different minzoom values", UserWarning
            )
        minzoom = max(minzoom)

    if maxzoom is None:
        maxzoom = list(set([feat["properties"]["maxzoom"] for feat in results]))
        if len(maxzoom) > 1:
            warnings.warn(
                "Multiple MaxZoom, Assets have multiple resolution values", UserWarning
            )
        maxzoom = max(maxzoom)

    quadkey_zoom = minzoom  # mosaic spec 0.0.2 WIP

    datatype = list(set([feat["properties"]["datatype"] for feat in results]))
    if len(datatype) > 1:
        raise Exception("Dataset should have the same data type")

    if not quiet:
        click.echo(f"Get quadkey list for zoom: {quadkey_zoom}", err=True)

    tiles = burntiles.burn(results, quadkey_zoom)
    tiles = ["{2}-{0}-{1}".format(*tile.tolist()) for tile in tiles]

    bounds = burntiles.find_extrema(results)

    if not quiet:
        click.echo(f"Feed Quadkey index", err=True)

    if version == "0.0.1":
        mosaic_definition = dict(
            minzoom=minzoom,
            maxzoom=maxzoom,
            bounds=bounds,
            center=[(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, minzoom],
            tiles={},
        )
    else:
        raise Exception(f"Invalid mosaicJSON version: {version}")

    dataset = [
        {"path": f["properties"]["path"], "geometry": shape(f["geometry"])}
        for f in results
    ]

    for parent in tiles:
        z, x, y = list(map(int, parent.split("-")))
        parent = mercantile.Tile(x=x, y=y, z=z)
        quad = mercantile.quadkey(*parent)
        tile_geometry = box(*mercantile.bounds(parent))
        fdataset = list(
            filter(lambda x: tile_geometry.intersects(x["geometry"]), dataset)
        )
        if minimum_tile_cover or tile_cover_sort:
            fdataset = _filter_and_sort(
                tile_geometry,
                fdataset,
                minimum_cover=minimum_tile_cover,
                sort_cover=tile_cover_sort,
            )

        if len(fdataset):
            mosaic_definition["tiles"][quad] = [f["path"] for f in fdataset]

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


def fetch_and_find_assets(mosaic_path: str, x: int, y: int, z: int) -> Tuple[str]:
    """Fetch mosaic definition file and find assets."""
    mosaic_def = fetch_mosaic_definition(mosaic_path)
    return get_assets(mosaic_def, x, y, z)


def get_assets(mosaic_definition: Dict, x: int, y: int, z: int) -> Tuple[str]:
    """Find assets."""
    min_zoom = mosaic_definition["minzoom"]
    max_zoom = mosaic_definition["maxzoom"]
    if z > max_zoom or z < min_zoom:
        return []  # return empty asset

    mercator_tile = mercantile.Tile(x=x, y=y, z=z)
    quadkey_zoom = mosaic_definition.get("quadkey_zoom", min_zoom)  # 0.0.2

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
        itertools.chain.from_iterable(
            [mosaic_definition["tiles"].get(qk, []) for qk in quadkey]
        )
    )

    # check if we have a mosaic in the url (.json/.gz)
    return list(
        itertools.chain.from_iterable(
            [
                fetch_and_find_assets(asset, x, y, z)
                if os.path.splitext(asset)[1] in [".json", ".gz"]
                else [asset]
                for asset in assets
            ]
        )
    )
