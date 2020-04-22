"""tests cogeo_mosaic.utils."""

import os
import json
from concurrent import futures

import pytest

import mercantile
from cogeo_mosaic import utils


mosaic_gz = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
mosaic_json = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")

asset1_uint32 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1_uint32.tif")
asset1_small = os.path.join(os.path.dirname(__file__), "fixtures", "cog1_small.tif")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set fake env to make sure we don't hit AWS services."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "jqt")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "rde")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/tmp/noconfigheere")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/tmp/noconfighereeither")
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "TRUE")


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


def test_mosaic_create():
    """Fetch info from dataset and create the mosaicJSON definition."""
    assets = [asset1, asset2]
    mosaic = utils.create_mosaic(assets, quiet=False)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]
    assert mosaic["minzoom"] == mosaic_content["minzoom"]
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())
    assert mosaic["quadkey_zoom"] == 7

    mosaic = utils.create_mosaic(assets, minzoom=7, maxzoom=9)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]
    assert mosaic["minzoom"] == mosaic_content["minzoom"]
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

    # 5% tile cover filter
    mosaic = utils.create_mosaic(assets, minimum_tile_cover=0.05)
    assert not list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

    # sort by tile cover
    mosaic = utils.create_mosaic(assets, tile_cover_sort=True)
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())
    assert not mosaic["tiles"] == mosaic_content["tiles"]

    mosaic = utils.create_mosaic(assets, quiet=False, quadkey_zoom=6)
    assert mosaic["quadkey_zoom"] == 6
    qk, _ = list(mosaic["tiles"].items())[0]
    tile = mercantile.quadkey_to_tile(qk)
    assert tile.z == 6

    mosaic = utils.create_mosaic(assets, quiet=False, version="0.0.1")
    assert not mosaic.get("quadkey_zoom")

    # Wrong MosaicJSON version
    with pytest.raises(Exception):
        utils.create_mosaic(assets, version="0.0.3")

    with pytest.warns(None) as record:
        mosaic = utils.create_mosaic([asset1_small, asset2], minzoom=7, maxzoom=9)
        assert not len(record)

    # Multiple MaxZoom
    with pytest.warns(UserWarning):
        assets = [asset1_small, asset2]
        utils.create_mosaic(assets)

    # Mixed datatype
    with pytest.raises(Exception):
        asset1_uint32
        assets = [asset1_uint32, asset2]
        utils.create_mosaic(assets)


def test_get_points():
    """Get points values for assets."""
    assets = [asset1, asset2]
    assert len(utils.get_point_values(assets, -73, 45)) == 2
    assert len(utils.get_point_values(assets, -75, 45)) == 1
    assert len(utils.get_point_values(assets, -60, 47)) == 0


def test_tiles_to_bounds():
    """Get tiles bounds for zoom level."""
    tiles = [mercantile.Tile(x=150, y=182, z=9), mercantile.Tile(x=151, y=182, z=9)]
    assert len(utils.tiles_to_bounds(tiles)) == 4


def test_update_mosaic():
    """Create mosaic and update it."""
    mosaic = utils.create_mosaic([asset1], minzoom=9)
    assert len(mosaic["tiles"]) == 36

    mosaic = utils.create_mosaic([asset1], minzoom=9)
    assert mosaic["version"] == "1.0.0"
    utils.update_mosaic([asset2], mosaic)
    assert len(mosaic["tiles"]) == 48
    assert len(mosaic["tiles"]["030230132"]) == 2
    assert mosaic["version"] == "1.0.1"

    mosaic = utils.create_mosaic([asset1], minzoom=9)
    utils.update_mosaic([asset2], mosaic, minimum_tile_cover=0.1)
    assert len(mosaic["tiles"]) == 47
    assert len(mosaic["tiles"]["030230132"]) == 1
