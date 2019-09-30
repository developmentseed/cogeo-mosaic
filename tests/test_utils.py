"""tests cogeo_mosaic.utils."""

import os
import json
from io import BytesIO

import pytest
from mock import patch

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


def test_decompress():
    """Test valid gz decompression."""
    with open(mosaic_gz, "rb") as f:
        body = f.read()
    res = json.loads(utils._decompress_gz(body))
    assert list(res.keys()) == ["minzoom", "maxzoom", "bounds", "center", "tiles"]


def test_compress():
    """Test valid gz compression."""
    with open(mosaic_json, "r") as f:
        mosaic = json.loads(f.read())

    body = utils._compress_gz_json(mosaic)
    assert type(body) == bytes
    res = json.loads(utils._decompress_gz(body))
    assert res == mosaic


@patch("cogeo_mosaic.utils.boto3_session")
def test_aws_put_data_valid(session):
    """Create a file on S3."""
    session.return_value.client.return_value.put_object.return_value = True

    body = b"1111111"
    bucket = "my-bucket"
    key = "myfile.json.gz"

    res = utils._aws_put_data(key, bucket, body)
    session.assert_called_once()
    assert res == key


@patch("cogeo_mosaic.utils.boto3_session")
def test_aws_get_data_valid(session):
    """Create a file on S3."""
    session.return_value.client.return_value.get_object.return_value = {
        "Body": BytesIO(b"1111111")
    }

    bucket = "my-bucket"
    key = "myfile.json.gz"

    res = utils._aws_get_data(key, bucket)
    session.assert_called_once()
    assert res == b"1111111"


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
    mosaic = utils.create_mosaic(assets)
    assert [round(b, 3) for b in mosaic["bounds"]] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic["maxzoom"] == mosaic_content["maxzoom"]
    assert mosaic["minzoom"] == mosaic_content["minzoom"]
    assert list(mosaic["tiles"].keys()) == list(mosaic_content["tiles"].keys())

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

    # Wrong MosaicJSON version
    with pytest.raises(Exception):
        utils.create_mosaic(assets, version="0.0.2")

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


class MockResponse:
    def __init__(self, data):
        self.data = data

    @property
    def content(self):
        return self.data


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_HttpContent(requests, s3get):
    """Download mosaic file from http."""
    with open(mosaic_json, "r") as f:
        requests.get.return_value = MockResponse(f.read())

    mosaic = utils.get_mosaic_content("https://mymosaic.json")
    assert mosaic == mosaic_content
    s3get.assert_not_called()
    requests.get.assert_called_once()


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_HttpContentGz(requests, s3get):
    """Download Gzip mosaic file from http."""
    with open(mosaic_gz, "rb") as f:
        requests.get.return_value = MockResponse(f.read())

    mosaic = utils.get_mosaic_content("https://mymosaic.json.gz")
    assert mosaic == mosaic_content
    s3get.assert_not_called()
    requests.get.assert_called_once()


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_S3Content(requests, s3get):
    """Download mosaic file from S3."""
    with open(mosaic_json, "r") as f:
        s3get.return_value = f.read()

    mosaic = utils.get_mosaic_content("s3://mybucket/mymosaic.json")
    assert mosaic == mosaic_content
    requests.get.assert_not_called()
    s3get.assert_called_once()


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_S3ContentGz(requests, s3get):
    """Download Gzip mosaic file from S3."""
    with open(mosaic_gz, "rb") as f:
        s3get.return_value = f.read()

    mosaic = utils.get_mosaic_content("s3://mybucket/mymosaic.json.gz")
    assert mosaic == mosaic_content
    requests.get.assert_not_called()
    s3get.assert_called_once()


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_Content(requests, s3get):
    """Download mosaic file."""
    mosaic = utils.get_mosaic_content(mosaic_json)
    assert mosaic == mosaic_content
    requests.get.assert_not_called()
    s3get.assert_not_called()


@patch("cogeo_mosaic.utils._aws_get_data")
@patch("cogeo_mosaic.utils.requests")
def test_get_mosaic_ContentGz(requests, s3get):
    """Download Gzip mosaic."""
    mosaic = utils.get_mosaic_content(mosaic_gz)
    assert mosaic == mosaic_content
    requests.get.assert_not_called()
    s3get.assert_not_called()


@patch("cogeo_mosaic.utils.fetch_mosaic_definition")
def test_get_assets(getMosaic):
    """Fetch mosaic and get assets list."""
    getMosaic.return_value = mosaic_content
    assert len(utils.fetch_and_find_assets("mymosaic.json", 150, 182, 9)) == 2
    assert len(utils.fetch_and_find_assets("mymosaic.json", 147, 182, 9)) == 1
    assert len(utils.fetch_and_find_assets("mymosaic.json", 147, 182, 12)) == 0
