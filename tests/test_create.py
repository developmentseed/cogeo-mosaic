import json
import os

import pytest

from cogeo_mosaic.create import create_mosaic

mosaic_gz = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
mosaic_json = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")

asset1_uint32 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1_uint32.tif")
asset1_small = os.path.join(os.path.dirname(__file__), "fixtures", "cog1_small.tif")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())


def test_mosaic_create():
    """Fetch info from dataset and create the mosaicJSON definition."""
    assets = [asset1, asset2]
    mosaic = create_mosaic(assets, quiet=False)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]
    assert mosaic["minzoom"] == mosaic_content["minzoom"]
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

    mosaic = create_mosaic(assets, minzoom=7, maxzoom=9)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]
    assert mosaic["minzoom"] == mosaic_content["minzoom"]
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

    # 5% tile cover filter
    mosaic = create_mosaic(assets, minimum_tile_cover=0.05)
    assert not list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

    # sort by tile cover
    mosaic = create_mosaic(assets, tile_cover_sort=True)
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())
    assert not mosaic["tiles"] == mosaic_content["tiles"]

    assets = [asset1, asset2]
    mosaic = create_mosaic(assets)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]

    # Wrong MosaicJSON version
    with pytest.raises(Exception):
        create_mosaic(assets, version="0.0.3")

    with pytest.warns(None) as record:
        mosaic = create_mosaic([asset1_small, asset2], minzoom=7, maxzoom=9)
        assert not len(record)

    # Multiple MaxZoom
    with pytest.warns(UserWarning):
        assets = [asset1_small, asset2]
        create_mosaic(assets)

    # Mixed datatype
    with pytest.raises(Exception):
        asset1_uint32
        assets = [asset1_uint32, asset2]
        create_mosaic(assets)
