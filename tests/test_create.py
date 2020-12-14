import json
import os

import pytest

from cogeo_mosaic.mosaic import MosaicJSON, default_filter

basepath = os.path.join(os.path.dirname(__file__), "fixtures")
mosaic_gz = os.path.join(basepath, "mosaic.json.gz")
mosaic_json = os.path.join(basepath, "mosaic.json")
asset1 = os.path.join(basepath, "cog1.tif")
asset2 = os.path.join(basepath, "cog2.tif")

asset1_uint32 = os.path.join(basepath, "cog1_uint32.tif")
asset1_small = os.path.join(basepath, "cog1_small.tif")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())
    for qk, asset in mosaic_content["tiles"].items():
        mosaic_content["tiles"][qk] = [os.path.join(basepath, item) for item in asset]


def _filter_and_sort(*args, **kwargs):
    dataset = default_filter(*args, **kwargs)
    return sorted(dataset, key=lambda x: x["properties"]["path"], reverse=True)


def test_mosaic_create():
    """Fetch info from dataset and create the mosaicJSON definition."""
    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets, quiet=False)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert mosaic.tiles == mosaic_content["tiles"]

    mosaic = MosaicJSON.from_urls(assets, minzoom=6, maxzoom=8)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    # 5% tile cover filter
    mosaic = MosaicJSON.from_urls(assets, minimum_tile_cover=0.059)
    assert not list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    # sort by tile cover
    mosaic = MosaicJSON.from_urls(assets, tile_cover_sort=True)
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert not mosaic.tiles == mosaic_content["tiles"]

    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]

    with pytest.warns(None) as record:
        MosaicJSON.from_urls([asset1_small, asset2], minzoom=7, maxzoom=9)
        assert not len(record)

    # Multiple MaxZoom
    with pytest.warns(UserWarning):
        assets = [asset1_small, asset2]
        MosaicJSON.from_urls(assets)

    # Mixed datatype
    with pytest.raises(Exception):
        asset1_uint32
        assets = [asset1_uint32, asset2]
        MosaicJSON.from_urls(assets)

    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets, asset_filter=_filter_and_sort, quiet=False)
    assert not mosaic.tiles == mosaic_content["tiles"]
