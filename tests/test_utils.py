"""tests cogeo_mosaic.utils."""

import os
from concurrent import futures

import mercantile
import pytest

from cogeo_mosaic import utils
from cogeo_mosaic.mosaic import MosaicJSON

asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")


def test_filtering_futurestask():
    """Should filter failed task."""

    def _is_odd(val: int) -> int:
        if not val % 2:
            raise Exception(f"{val} is Even.")
        return val

    with futures.ThreadPoolExecutor() as executor:
        future_work = [executor.submit(_is_odd, item) for item in range(0, 8)]
    assert list(utils._filter_futures(future_work)) == [1, 3, 5, 7]

    with pytest.raises(Exception):
        with futures.ThreadPoolExecutor() as executor:
            future_work = [executor.submit(_is_odd, item) for item in range(0, 8)]
        list([f.result() for f in future_work])


def test_dataset_info():
    """Read raster metadata and return spatial info."""
    info = utils.get_dataset_info(asset1)
    assert info["geometry"]
    assert info["properties"]["path"]
    assert info["properties"]["bounds"]
    assert info["properties"]["datatype"]
    assert info["properties"]["minzoom"] == 7
    assert info["properties"]["maxzoom"] == 9


def test_footprint():
    """Fetch footprints from asset list."""
    assets = [asset1, asset2]
    foot = utils.get_footprints(assets)
    assert len(foot) == 2


def test_tiles_to_bounds():
    """Get tiles bounds for zoom level."""
    tiles = [mercantile.Tile(x=150, y=182, z=9), mercantile.Tile(x=151, y=182, z=9)]
    assert len(utils.tiles_to_bounds(tiles)) == 4


def test_update_mosaic():
    """Create mosaic and update it."""
    mosaic = MosaicJSON.from_urls([asset1], minzoom=9).dict(exclude_none=True)
    assert len(mosaic["tiles"]) == 36

    mosaic = MosaicJSON.from_urls([asset1], minzoom=9).dict(exclude_none=True)
    assert mosaic["version"] == "1.0.0"
    utils.update_mosaic([asset2], mosaic)

    assert len(mosaic["tiles"]) == 48
    assert len(mosaic["tiles"]["030230132"]) == 2
    assert mosaic["version"] == "1.0.1"

    mosaic = MosaicJSON.from_urls([asset1], minzoom=9).dict(exclude_none=True)
    utils.update_mosaic([asset2], mosaic, minimum_tile_cover=0.1)
    assert len(mosaic["tiles"]) == 47
    assert len(mosaic["tiles"]["030230132"]) == 1
