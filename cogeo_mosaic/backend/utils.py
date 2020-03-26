import functools
import itertools
import os
from typing import Dict, Tuple

import mercantile


def get_assets_from_json(mosaic_definition: Dict, x: int, y: int, z: int) -> Tuple[str]:
    """Find assets."""
    min_zoom = mosaic_definition["minzoom"]

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
