"""cogeo-mosaic.backends utility functions."""

import hashlib
import itertools
import json
import os
import zlib
from typing import Any, Dict, List

import mercantile


def find_quadkeys(mercator_tile: mercantile.Tile, quadkey_zoom: int) -> List[str]:
    """
    Find quadkeys at desired zoom for tile

    Attributes
    ----------
    mercator_tile: mercantile.Tile
        Input tile to use when searching for quadkeys
    quadkey_zoom: int
        Zoom level

    Returns
    -------
    list
        List[str] of quadkeys

    """
    # get parent
    if mercator_tile.z > quadkey_zoom:
        depth = mercator_tile.z - quadkey_zoom
        for i in range(depth):
            mercator_tile = mercantile.parent(mercator_tile)
        return [mercantile.quadkey(*mercator_tile)]

    # get child
    elif mercator_tile.z < quadkey_zoom:
        depth = quadkey_zoom - mercator_tile.z
        mercator_tiles = [mercator_tile]
        for i in range(depth):
            mercator_tiles = sum([mercantile.children(t) for t in mercator_tiles], [])

        mercator_tiles = list(filter(lambda t: t.z == quadkey_zoom, mercator_tiles))
        return [mercantile.quadkey(*tile) for tile in mercator_tiles]
    else:
        return [mercantile.quadkey(*mercator_tile)]


def get_assets_from_json(
    tiles: Dict, quadkey_zoom: int, x: int, y: int, z: int
) -> List[str]:
    """Find assets."""
    mercator_tile = mercantile.Tile(x=x, y=y, z=z)
    quadkeys = find_quadkeys(mercator_tile, quadkey_zoom)

    assets = list(itertools.chain.from_iterable([tiles.get(qk, []) for qk in quadkeys]))

    # check if we have a mosaic in the url (.json/.gz)
    return list(
        itertools.chain.from_iterable(
            [
                get_assets_from_json(tiles, quadkey_zoom, x, y, z)
                if os.path.splitext(asset)[1] in [".json", ".gz"]
                else [asset]
                for asset in assets
            ]
        )
    )


def _compress_gz_json(data: Dict) -> bytes:
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    return (
        gzip_compress.compress(json.dumps(data).encode("utf-8")) + gzip_compress.flush()
    )


def _decompress_gz(gzip_buffer: bytes):
    return zlib.decompress(gzip_buffer, zlib.MAX_WBITS | 16).decode()


def get_hash(**kwargs: Any) -> str:
    """Create hash from a dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()
    ).hexdigest()
