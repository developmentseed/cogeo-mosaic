"""Test backends utils."""

import json
import os
import re

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
    assert sorted(res.keys()) == sorted(
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

    body = utils._compress_gz_json(json.dumps(mosaic))
    assert type(body) == bytes
    res = json.loads(utils._decompress_gz(body))
    assert res == mosaic


def test_hash():
    """Should return a 56 characters long string."""
    hash = utils.get_hash(a=1)
    assert re.match(r"[0-9A-Fa-f]{56}", hash)
