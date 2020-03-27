import functools
import itertools
import os
from typing import Dict, List, Tuple

import mercantile


def find_quadkeys(mercator_tile: mercantile.Tile, quadkey_zoom: int) -> List[str]:
    """Find quadkeys at desired zoom for tile

    Attributes
    ----------
    mercator_tile: mercantile.Tile
        Input tile to use when searching for quadkeys
    quadkey_zoom: int
        Zoom level

    Returns
    -------
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


def get_assets_from_json(mosaic_definition: Dict, x: int, y: int, z: int) -> Tuple[str]:
    """Find assets."""
    min_zoom = mosaic_definition["minzoom"]

    mercator_tile = mercantile.Tile(x=x, y=y, z=z)
    quadkey_zoom = mosaic_definition.get("quadkey_zoom", min_zoom)  # 0.0.2

    quadkeys = find_quadkeys(mercator_tile, quadkey_zoom)

    assets = list(
        itertools.chain.from_iterable(
            [mosaic_definition["tiles"].get(qk, []) for qk in quadkeys]
        )
    )

    # check if we have a mosaic in the url (.json/.gz)
    return list(
        itertools.chain.from_iterable(
            [
                get_assets_from_json(asset, x, y, z)
                if os.path.splitext(asset)[1] in [".json", ".gz"]
                else [asset]
                for asset in assets
            ]
        )
    )
