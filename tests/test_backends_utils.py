"""Test backends utils."""

import json
import os
import re

import mercantile

from cogeo_mosaic.backends import utils

mosaic_gz = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
mosaic_json = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())


def test_decompress():
    """Test valid gz decompression."""
    with open(mosaic_gz, "rb") as f:
        body = f.read()
    res = json.loads(utils._decompress_gz(body))
    assert sorted(list(res.keys())) == sorted(
        [
            "mosaicjson",
            "quadkey_zoom",
            "minzoom",
            "maxzoom",
            "bounds",
            "center",
            "tiles",
            "version",
        ]
    )


def test_compress():
    """Test valid gz compression."""
    with open(mosaic_json, "r") as f:
        mosaic = json.loads(f.read())

    body = utils._compress_gz_json(mosaic)
    assert type(body) == bytes
    res = json.loads(utils._decompress_gz(body))
    assert res == mosaic


def test_hash():
    """Should return a 56 characters long string."""
    hash = utils.get_hash(a=1)
    assert re.match(r"[0-9A-Fa-f]{56}", hash)


def test_find_quadkeys():
    """Get correct quadkeys"""
    tile = mercantile.Tile(150, 182, 9)
    assert utils.find_quadkeys(tile, 8) == ["03023033"]
    assert utils.find_quadkeys(tile, 9) == ["030230330"]
    assert utils.find_quadkeys(tile, 10) == [
        "0302303300",
        "0302303301",
        "0302303303",
        "0302303302",
    ]
