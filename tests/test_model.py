import json
import os

import morecantile
import pytest
from pydantic import BaseModel, ValidationError

from cogeo_mosaic.mosaic import MosaicJSON

basepath = os.path.join(os.path.dirname(__file__), "fixtures")
mosaic_json = os.path.join(basepath, "mosaic.json")
asset1 = os.path.join(basepath, "cog1.tif")
asset2 = os.path.join(basepath, "cog2.tif")


def test_model():
    with open(mosaic_json) as f:
        mosaic = MosaicJSON(**json.load(f))
        assert isinstance(mosaic.bounds, tuple)
        assert isinstance(mosaic.center, tuple)
        assert isinstance(mosaic, BaseModel)


def test_validation_error():
    with open(mosaic_json) as f:
        data = json.load(f)
        data["minzoom"] = -1
        with pytest.raises(ValidationError):
            MosaicJSON(**data)


def test_compute_center():
    with open(mosaic_json) as f:
        data = json.load(f)
        del data["center"]
        mosaic = MosaicJSON(**data)
        assert mosaic.center


def test_validate_assignment():
    with open(mosaic_json) as f:
        mosaic = MosaicJSON(**json.load(f))
        with pytest.raises(ValidationError):
            mosaic.minzoom = -1


def test_mosaic_reverse():
    """MosaicJSON dict can be reversed"""
    assets = [asset1, asset2]
    tms = morecantile.tms.get("WebMercatorQuad")
    mosaic = MosaicJSON.from_urls(assets, quiet=True, tilematrixset=tms)

    mosaic_dict = mosaic.dict(exclude_none=True)
    assert MosaicJSON(**mosaic_dict).tilematrixset.id == "WebMercatorQuad"

    mosaic_json = mosaic.json(exclude_none=True)
    assert MosaicJSON(**json.loads(mosaic_json)).tilematrixset.id == "WebMercatorQuad"
