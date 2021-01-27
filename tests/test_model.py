import json
import os

import pytest
from pydantic import BaseModel, ValidationError

from cogeo_mosaic.mosaic import MosaicJSON

basepath = os.path.join(os.path.dirname(__file__), "fixtures")
mosaic_json = os.path.join(basepath, "mosaic.json")


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
