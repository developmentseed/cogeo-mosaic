import json
import os

import pytest

from cogeo_mosaic.mosaic import MosaicJSON, default_filter

basepath = os.path.join(os.path.dirname(__file__), "fixtures")
mosaic_gz = os.path.join(basepath, "mosaic.json.gz")
mosaic_json = os.path.join(basepath, "mosaic.json")
item1 = os.path.join(basepath, "cog1.tif")
item2 = os.path.join(basepath, "cog2.tif")

item1_uint32 = os.path.join(basepath, "cog1_uint32.tif")
item1_small = os.path.join(basepath, "cog1_small.tif")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())
    for qk, asset in mosaic_content["tiles"].items():
        mosaic_content["tiles"][qk] = [os.path.join(basepath, item) for item in asset]


def _filter_and_sort(*args, **kwargs):
    dataset = default_filter(*args, **kwargs)
    return sorted(dataset, key=lambda x: x["properties"]["path"], reverse=True)


def test_mosaic_create():
    """Fetch info from dataset and create the mosaicJSON definition."""
    items = [item1, item2]
    mosaic = MosaicJSON.from_urls(items, quiet=False)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert mosaic.tiles == mosaic_content["tiles"]

    mosaic = MosaicJSON.from_urls(items, minzoom=7, maxzoom=9)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    # 5% tile cover filter
    mosaic = MosaicJSON.from_urls(items, minimum_tile_cover=0.059)
    assert not list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    # sort by tile cover
    mosaic = MosaicJSON.from_urls(items, tile_cover_sort=True)
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert not mosaic.tiles == mosaic_content["tiles"]

    items = [item1, item2]
    mosaic = MosaicJSON.from_urls(items)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]

    with pytest.warns(None) as record:
        MosaicJSON.from_urls([item1_small, item2], minzoom=7, maxzoom=9)
        assert not len(record)

    # Multiple MaxZoom
    with pytest.warns(UserWarning):
        items = [item1_small, item2]
        MosaicJSON.from_urls(items)

    # Mixed datatype
    with pytest.raises(Exception):
        item1_uint32
        items = [item1_uint32, item2]
        MosaicJSON.from_urls(items)

    items = [item1, item2]
    mosaic = MosaicJSON.from_urls(items, item_filter=_filter_and_sort, quiet=False)
    assert not mosaic.tiles == mosaic_content["tiles"]
