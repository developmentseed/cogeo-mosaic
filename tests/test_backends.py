"""Test backends."""

import json
import os
import time
from decimal import Decimal
from io import BytesIO
from typing import Dict, List
from unittest.mock import patch

import boto3
import morecantile
import numpy
import pytest
from click.testing import CliRunner
from httpx import HTTPStatusError, RequestError
from pydantic import ValidationError
from rio_tiler.errors import PointOutsideBounds

from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.backends.az import ABSBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.gs import GCSBackend
from cogeo_mosaic.backends.memory import MemoryBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.sqlite import SQLiteBackend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.stac import _fetch as stac_search
from cogeo_mosaic.backends.stac import default_stac_accessor as stac_accessor
from cogeo_mosaic.backends.utils import _decompress_gz
from cogeo_mosaic.backends.web import HttpBackend
from cogeo_mosaic.errors import (
    MosaicError,
    MosaicExistsError,
    MosaicNotFoundError,
    NoAssetFoundError,
)
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import get_footprints

mosaic_gz = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
mosaic_db = os.path.join(os.path.dirname(__file__), "fixtures", "mosaics.db")
mosaic_json = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
mosaic_jsonV1 = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic_0.0.1.json")
stac_page1 = os.path.join(os.path.dirname(__file__), "fixtures", "stac_p1.geojson")
stac_page2 = os.path.join(os.path.dirname(__file__), "fixtures", "stac_p2.geojson")
asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())


def test_file_backend():
    """Test File backend."""
    with MosaicBackend(mosaic_gz) as mosaic:
        assert mosaic._backend_name == "File"
        assert isinstance(mosaic, FileBackend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )
        assert mosaic.quadkey_zoom == 7
        assert mosaic.minzoom == mosaic.mosaic_def.minzoom

        info = mosaic.info()
        assert not info.quadkeys
        with pytest.warns(DeprecationWarning):
            assert not info["quadkeys"]

        assert list(info.model_dump()) == [
            "bounds",
            "center",
            "minzoom",
            "maxzoom",
            "name",
            "quadkeys",
            "tilematrixset",
        ]

        info = mosaic.info(quadkeys=True)
        assert info.quadkeys

        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        # make sure we do not return asset twice (e.g for parent tile)
        assert mosaic.assets_for_tile(18, 22, 6) == ["cog1.tif", "cog2.tif"]

        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]

        assert len(mosaic.get_assets(150, 182, 9)) == 2
        assert len(mosaic.get_assets(147, 182, 12)) == 0

        assert mosaic.assets_for_bbox(
            -74.53125, 45.583289756006316, -73.828125, 46.07323062540836
        ) == ["cog1.tif", "cog2.tif"]

    with MosaicBackend(mosaic_json) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert mosaic.quadkey_zoom == 7

    with MosaicBackend(mosaic_jsonV1) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == ["mosaicjson", "version", "minzoom", "maxzoom", "bounds", "center"]

    with pytest.raises(ValidationError):
        with MosaicBackend("afile.json", mosaic_def={}):
            pass

    runner = CliRunner()
    with runner.isolated_filesystem():
        with MosaicBackend("mosaic.json", mosaic_def=mosaic_content) as mosaic:
            mosaic.write()
            assert mosaic.minzoom == mosaic_content["minzoom"]

            with open("mosaic.json") as f:
                m = json.loads(f.read())
                assert m["quadkey_zoom"] == 7
            with pytest.raises(MosaicExistsError):
                mosaic.write()
            mosaic.write(overwrite=True)

        with MosaicBackend("mosaic.json.gz", mosaic_def=mosaic_content) as mosaic:
            mosaic.write()
            with open("mosaic.json.gz", "rb") as f:
                m = json.loads(_decompress_gz(f.read()))
                assert m["quadkey_zoom"] == 7

        mosaic_oneasset = MosaicJSON.from_urls([asset1], quiet=True)

        with MosaicBackend("umosaic.json.gz", mosaic_def=mosaic_oneasset) as mosaic:
            mosaic.write()
            assert len(mosaic.get_assets(150, 182, 9)) == 1

        with MosaicBackend("umosaic.json.gz") as mosaic:
            features = get_footprints([asset2], quiet=True)
            mosaic.update(features)
            assets = mosaic.get_assets(150, 182, 9)
            assert len(assets) == 2
            assert assets[0] == asset2
            assert assets[1] == asset1

        with MosaicBackend("umosaic.json.gz") as mosaic:
            tile = morecantile.Tile(150, 182, 9)
            assert mosaic.find_quadkeys(tile, 8) == ["03023033"]
            assert mosaic.find_quadkeys(tile, 9) == ["030230330"]
            assert sorted(mosaic.find_quadkeys(tile, 10)) == sorted(
                [
                    "0302303300",
                    "0302303301",
                    "0302303303",
                    "0302303302",
                ]
            )

    with MosaicBackend(mosaic_gz) as mosaic:
        tile = mosaic.tms.tile(mosaic.center[0], mosaic.center[1], mosaic.minzoom)

        assert mosaic.assets_for_tile(*tile) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_bbox(
            *mosaic.tms.xy_bounds(*tile), coord_crs=mosaic.tms.rasterio_crs
        ) == ["cog1.tif", "cog2.tif"]

        assert mosaic.assets_for_bbox(
            *mosaic.tms.bounds(*tile),
            coord_crs=mosaic.tms.rasterio_geographic_crs,
        ) == ["cog1.tif", "cog2.tif"]

        assert mosaic.assets_for_point(
            -73.662319,
            46.015949,
            coord_crs="epsg:4326",
        ) == ["cog1.tif", "cog2.tif"]

        assert mosaic.assets_for_point(
            -8200051.8694,
            5782905.49327,
            coord_crs="epsg:3857",
        ) == ["cog1.tif", "cog2.tif"]

    tms = morecantile.tms.get("WGS1984Quad")
    with MosaicBackend(mosaic_gz, tms=tms) as mosaic:
        assert mosaic.minzoom == tms.minzoom
        assert mosaic.maxzoom == tms.maxzoom

    with MosaicBackend(mosaic_gz, tms=tms, minzoom=6, maxzoom=8) as mosaic:
        assert mosaic.minzoom == 6
        assert mosaic.maxzoom == 8


class MockResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    @property
    def content(self):
        return self.data


@patch("cogeo_mosaic.backends.web.httpx")
def test_http_backend(httpx):
    """Test HTTP backend."""
    with open(mosaic_json, "r") as f:
        httpx.get.return_value = MockResponse(f.read())
        httpx.HTTPStatusError = HTTPStatusError
        httpx.RequestError = RequestError

    with MosaicBackend("https://mymosaic.json") as mosaic:
        assert mosaic._backend_name == "HTTP"
        assert isinstance(mosaic, HttpBackend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]
    httpx.get.assert_called_once()
    httpx.mock_reset()

    with open(mosaic_json, "r") as f:
        httpx.get.return_value = MockResponse(f.read())

    with pytest.raises(NotImplementedError):
        with MosaicBackend("https://mymosaic.json") as mosaic:
            mosaic.write()
        httpx.get.assert_called_once()
        httpx.mock_reset()

    with pytest.raises(NotImplementedError):
        with MosaicBackend("https://mymosaic.json") as mosaic:
            mosaic.update([])
        httpx.get.assert_called_once()
        httpx.mock_reset()

    # The HttpBackend is Read-Only, you can't pass mosaic_def
    with pytest.raises(TypeError):
        with MosaicBackend("https://mymosaic.json", mosaic_def=mosaic_content) as mosaic:
            pass

    with open(mosaic_gz, "rb") as f:
        httpx.get.return_value = MockResponse(f.read())

    with MosaicBackend("https://mymosaic.json.gz") as mosaic:
        assert isinstance(mosaic, HttpBackend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )


@patch("cogeo_mosaic.backends.s3.boto3_session")
def test_s3_backend(session):
    """Test S3 backend."""
    with open(mosaic_gz, "rb") as f:
        session.return_value.client.return_value.get_object.return_value = {
            "Body": BytesIO(f.read())
        }
    session.return_value.client.return_value.put_object.return_value = True
    session.return_value.client.return_value.head_object.return_value = False

    with MosaicBackend("s3://mybucket/mymosaic.json.gz") as mosaic:
        assert mosaic._backend_name == "AWS S3"
        assert isinstance(mosaic, S3Backend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]
        session.return_value.client.return_value.get_object.assert_called_once_with(
            Bucket="mybucket", Key="mymosaic.json.gz"
        )
        session.return_value.client.return_value.put_object.assert_not_called()
        session.return_value.client.return_value.head_object.assert_not_called()
        session.reset_mock()

    with open(mosaic_gz, "rb") as f:
        session.return_value.client.return_value.get_object.return_value = {
            "Body": BytesIO(f.read())
        }
    session.return_value.client.return_value.put_object.return_value = True
    session.return_value.client.return_value.head_object.return_value = False

    with MosaicBackend(
        "s3://mybucket/mymosaic.json.gz", mosaic_def=mosaic_content
    ) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.client.return_value.head_object.assert_called_once()
    kwargs = session.return_value.client.return_value.put_object.call_args[1]
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "mymosaic.json.gz"
    assert MosaicJSON(**json.loads(_decompress_gz(kwargs["Body"])))
    session.reset_mock()

    session.return_value.client.return_value.head_object.return_value = False
    with MosaicBackend("s3://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.client.return_value.head_object.assert_called_once()
    kwargs = session.return_value.client.return_value.put_object.call_args[1]
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "00000.json"
    assert MosaicJSON(**json.loads(kwargs["Body"]))
    session.reset_mock()

    session.return_value.client.return_value.head_object.return_value = True
    with MosaicBackend("s3://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, S3Backend)
        with pytest.raises(MosaicExistsError):
            mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.client.return_value.head_object.assert_called_once()
    kwargs = session.return_value.client.return_value.put_object.assert_not_called()
    session.reset_mock()

    session.return_value.client.return_value.head_object.return_value = True
    with MosaicBackend("s3://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write(overwrite=True)
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.client.return_value.head_object.assert_not_called()
    kwargs = session.return_value.client.return_value.put_object.assert_called_once()
    session.reset_mock()


@patch("cogeo_mosaic.backends.gs.gcp_session")
def test_gs_backend(session):
    """Test GS backend."""
    with open(mosaic_gz, "rb") as f:
        session.return_value.bucket.return_value.blob.return_value.download_as_bytes.return_value = f.read()

    session.return_value.bucket.return_value.blob.return_value.upload_from_string.return_value = True
    session.return_value.bucket.return_value.blob.return_value.exists.return_value = False

    with MosaicBackend("gs://mybucket/mymosaic.json.gz") as mosaic:
        assert mosaic._backend_name == "Google Cloud Storage"
        assert isinstance(mosaic, GCSBackend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]
        session.return_value.bucket.assert_called_once_with("mybucket")
        session.return_value.bucket.return_value.blob.assert_called_once_with(
            "mymosaic.json.gz"
        )

        session.return_value.bucket.return_value.blob.return_value.upload_from_string.assert_not_called()
        session.return_value.bucket.return_value.blob.return_value.exists.assert_not_called()
        session.reset_mock()

    with open(mosaic_gz, "rb") as f:
        session.return_value.bucket.return_value.blob.return_value.download_as_bytes.return_value = f.read()

    session.return_value.bucket.return_value.blob.return_value.upload_from_string.return_value = True
    session.return_value.bucket.return_value.blob.return_value.exists.return_value = False

    with MosaicBackend(
        "gs://mybucket/mymosaic.json.gz", mosaic_def=mosaic_content
    ) as mosaic:
        assert isinstance(mosaic, GCSBackend)
        mosaic.write()
    session.return_value.bucket.return_value.blob.return_value.download_as_bytes.assert_not_called()

    session.return_value.bucket.return_value.blob.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.bucket.return_value.blob.return_value.exists.return_value = False
    with MosaicBackend("gs://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, GCSBackend)
        mosaic.write()
    session.return_value.bucket.return_value.blob.return_value.download_as_bytes.assert_not_called()
    session.return_value.bucket.return_value.blob.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.bucket.return_value.blob.return_value.exists.return_value = True
    with MosaicBackend("gs://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, GCSBackend)
        with pytest.raises(MosaicExistsError):
            mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.bucket.return_value.blob.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.bucket.return_value.blob.return_value.exists.return_value = True
    with MosaicBackend("gs://mybucket/00000.json", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, GCSBackend)
        mosaic.write(overwrite=True)
    session.return_value.client.return_value.get_object.assert_not_called()
    session.return_value.client.return_value.head_object.assert_not_called()
    session.reset_mock()


@patch("cogeo_mosaic.backends.az.BlobServiceClient")
def test_abs_backend(session):
    """Test ABS backend."""
    with open(mosaic_gz, "rb") as f:
        session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.return_value.readall.return_value = f.read()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.upload_blob.return_value = True
    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.return_value = False

    with MosaicBackend(
        "az://storage_account.blob.core.windows.net/container/mymosaic.json.gz"
    ) as mosaic:
        assert mosaic._backend_name == "Azure Blob Storage"
        assert isinstance(mosaic, ABSBackend)
        assert (
            mosaic.mosaicid == "24d43802c19ef67cc498c327b62514ecf70c2bbb1bbc243dda1ee075"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]
        session.return_value.get_container_client.assert_called_once_with("container")
        session.return_value.get_container_client.return_value.get_blob_client.assert_called_once_with(
            "mymosaic.json.gz"
        )

        session.return_value.get_container_client.return_value.get_blob_client.return_value.upload_blob.assert_not_called()
        session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.assert_not_called()
        session.reset_mock()

    with open(mosaic_gz, "rb") as f:
        session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.return_value.readall.return_value = f.read()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.upload_blob.return_value = True
    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.return_value = False

    with MosaicBackend(
        "az://storage_account.blob.core.windows.net/container/mymosaic.json.gz",
        mosaic_def=mosaic_content,
    ) as mosaic:
        assert isinstance(mosaic, ABSBackend)
        mosaic.write()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.assert_not_called()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.return_value = False
    with MosaicBackend(
        "az://storage_account.blob.core.windows.net/container/00000.json",
        mosaic_def=mosaic_content,
    ) as mosaic:
        assert isinstance(mosaic, ABSBackend)
        mosaic.write()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.assert_not_called()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.return_value = True
    with MosaicBackend(
        "az://storage_account.blob.core.windows.net/container/00000.json",
        mosaic_def=mosaic_content,
    ) as mosaic:
        assert isinstance(mosaic, ABSBackend)
        with pytest.raises(MosaicExistsError):
            mosaic.write()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.assert_not_called()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.assert_called_once()
    session.reset_mock()

    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.return_value = True
    with MosaicBackend(
        "az://storage_account.blob.core.windows.net/container/00000.json",
        mosaic_def=mosaic_content,
    ) as mosaic:
        assert isinstance(mosaic, ABSBackend)
        mosaic.write(overwrite=True)
    session.return_value.get_container_client.return_value.get_blob_client.return_value.download_blob.assert_not_called()
    session.return_value.get_container_client.return_value.get_blob_client.return_value.exists.assert_not_called()
    session.reset_mock()


class MockMeta(object):
    """Mock Meta."""

    def __init__(self):
        pass

    @property
    def client(self):
        return boto3.client("dynamodb", region_name="us-east-1")


class MockTable(object):
    """Mock Dynamo DB."""

    def __init__(self, name):
        self.table_name = name

    def create_table(
        self,
        AttributeDefinitions: List,
        TableName: str,
        KeySchema: List,
        BillingMode: str,
    ):
        assert TableName == "thiswaskylebarronidea"
        return True

    def wait_until_exists(self):
        time.sleep(1)
        return True

    def wait_until_not_exists(self):
        time.sleep(1)
        return True

    def delete(self):
        pass

    @property
    def meta(self):
        return MockMeta()

    @property
    def table_status(self):
        raise self.meta.client.exceptions.ResourceNotFoundException(
            error_response={}, operation_name="table_status"
        )

    def get_item(self, Key: Dict = None) -> Dict:
        """Mock Get Item."""
        Key = Key or {}

        quadkey = Key["quadkey"]
        if quadkey == "-1":
            return {
                "Item": {
                    "mosaicjson": "0.0.2",
                    "version": "1.0.0",
                    "minzoom": 7,
                    "maxzoom": 8,
                    "quadkey_zoom": 7,
                    "bounds": [
                        Decimal("-75.98703377403767"),
                        Decimal("44.93504283293786"),
                        Decimal("-71.337604723999"),
                        Decimal("47.09685599202324"),
                    ],
                    "center": [
                        Decimal("-73.66231924906833"),
                        Decimal("46.01594941248055"),
                        7,
                    ],
                }
            }

        items = mosaic_content["tiles"].get(quadkey)
        if not items:
            return {}
        return {"Item": {"assets": items}}

    def query(self, *args, **kwargs):
        """Mock Scan."""
        mosaic = MosaicJSON(**mosaic_content)
        return {
            "Items": [
                {"quadkey": qk, "assets": assets} for qk, assets in mosaic.tiles.items()
            ]
        }


@patch("cogeo_mosaic.backends.dynamodb.boto3.resource")
def test_dynamoDB_backend(client):
    """Test DynamoDB backend."""
    client.return_value.Table = MockTable

    with MosaicBackend("dynamodb:///thiswaskylebarronidea:mosaic") as mosaic:
        assert mosaic._backend_name == "AWS DynamoDB"
        assert isinstance(mosaic, DynamoDBBackend)
        assert mosaic.quadkey_zoom == 7
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]

        info = mosaic.info()
        assert not info.quadkeys
        assert list(info.model_dump()) == [
            "bounds",
            "center",
            "minzoom",
            "maxzoom",
            "name",
            "quadkeys",
            "tilematrixset",
        ]

        info = mosaic.info(quadkeys=True)
        assert info.quadkeys

    # TODO better test dynamodb write
    # with MosaicBackend(
    #     "dynamodb:///thiswaskylebarronidea:mosaic2", mosaic_def=mosaic_content
    # ) as mosaic:
    #     assert isinstance(mosaic, DynamoDBBackend)
    #     items = mosaic._create_items()
    #     assert len(items) == 10
    #     assert items[-1] == {
    #         "mosaicId": "mosaic2",
    #         "quadkey": "0302330",
    #         "assets": ["cog1.tif", "cog2.tif"],
    #     }
    #     mosaic._create_table()

    # with MosaicBackend(
    #     "dynamodb:///thiswaskylebarronidea:mosaic2", mosaic_def=mosaic_content
    # ) as mosaic:
    #     items = mosaic._create_items()
    #     assert len(items) == len(mosaic.mosaic_def.tiles.items()) + 1
    #     assert "quadkey" in list(items[0])
    #     assert "mosaicId" in list(items[0])
    #     assert "bounds" in list(items[0])
    #     assert "center" in list(items[0])


class STACMockResponse(MockResponse):
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


@patch("cogeo_mosaic.backends.stac.httpx.post")
def test_stac_backend(post):
    """Test STAC backend."""
    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend(
        "https://a_stac.api/search", {}, 8, 14, stac_api_options={"max_items": 8}
    ) as mosaic:
        assert mosaic._backend_name == "STAC"
        assert isinstance(mosaic, STACBackend)
        assert post.call_count == 1
        assert mosaic.quadkey_zoom == 8
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(210, 90, 10) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
        assert mosaic.assets_for_point(-106.050, 81.43) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
    post.reset_mock()

    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend(
        "https://a_stac.api/search", {}, 8, 14, stac_api_options={"max_items": 15}
    ) as mosaic:
        assert mosaic._backend_name == "STAC"
        assert isinstance(mosaic, STACBackend)
        assert post.call_count == 2
        assert mosaic.quadkey_zoom == 8
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
    post.reset_mock()

    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend(
        "https://a_stac.api/search", {}, 8, 14, stac_api_options={"max_items": 15}
    ) as mosaic:
        with pytest.raises(NotImplementedError):
            mosaic.write()

        with pytest.raises(NotImplementedError):
            mosaic.update([])
    post.reset_mock()

    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend(
        "https://a_stac.api/search",
        {},
        tms=morecantile.tms.get("WGS1984Quad"),
        minzoom=8,
        maxzoom=13,
        stac_api_options={"max_items": 8},
        mosaic_options={
            "tilematrixset": morecantile.tms.get("WebMercatorQuad"),
            "minzoom": 8,
            "maxzoom": 14,
        },
    ) as mosaic:
        assert mosaic._backend_name == "STAC"
        assert isinstance(mosaic, STACBackend)
        assert mosaic.quadkey_zoom == 8
        assert mosaic.minzoom == 8
        assert mosaic.maxzoom == 13
        assert mosaic.mosaic_def.minzoom == 8
        assert mosaic.mosaic_def.maxzoom == 14
        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
            "tilematrixset",
        ]
        assert mosaic.assets_for_tile(420, 48, 10) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
        assert mosaic.assets_for_point(-106.050, 81.43) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
    post.reset_mock()


@patch("cogeo_mosaic.backends.stac.httpx.post")
def test_stac_search(post):
    """Test stac_search."""
    post.side_effect = [
        STACMockResponse({"context": {"returned": 0}}),
    ]
    assert stac_search("https://a_stac.api/search", {}, limit=10) == []

    with open(stac_page1, "r") as f1:
        resp = json.loads(f1.read())
        resp["links"] = []
        post.side_effect = [
            STACMockResponse(resp),
        ]

    assert len(stac_search("https://a_stac.api/search", {}, max_items=7)) == 7
    post.reset_mock()

    post.side_effect = [
        STACMockResponse(
            {"features": [{"id": "1"}], "context": {"returned": 1, "limit": 1}}
        ),
        STACMockResponse(
            {"features": [{"id": "2"}], "context": {"returned": 1, "limit": 1}}
        ),
    ]
    assert len(stac_search("https://a_stac.api/search", {}, max_items=2, limit=1)) == 2
    assert post.call_count == 2
    post.reset_mock()
    stac_search.cache_clear()

    post.side_effect = [
        STACMockResponse(
            {
                "features": [{"id": "1"}],
                "numberMatched": 2,
                "numberReturned": 1,
                "context": {},
            }
        ),
        STACMockResponse(
            {
                "features": [{"id": "2"}],
                "numberMatched": 2,
                "numberReturned": 1,
                "context": {},
            }
        ),
    ]
    assert len(stac_search("https://a_stac.api/search", {}, max_items=2, limit=1)) == 2
    assert post.call_count == 2
    post.reset_mock()


def test_stac_accessor():
    """Test stac_accessor."""
    # First return the `self` link
    feat = {
        "type": "Feature",
        "id": "S2A_11XNM_20200621_0_L2A",
        "collection": "sentinel-s2-l2a",
        "links": [
            {
                "rel": "self",
                "href": "https://a_stac.api/collections/sentinel-s2-l2a/items/S2A_11XNM_20200621_0_L2A",
            },
        ],
    }
    assert (
        stac_accessor(feat)
        == "https://a_stac.api/collections/sentinel-s2-l2a/items/S2A_11XNM_20200621_0_L2A"
    )

    # Construct the `self` link
    feat = {
        "type": "Feature",
        "id": "S2A_11XNM_20200621_0_L2A",
        "collection": "sentinel-s2-l2a",
        "links": [{"rel": "root", "href": "https://a_stac.api"}],
    }
    assert (
        stac_accessor(feat)
        == "https://a_stac.api/collections/sentinel-s2-l2a/items/S2A_11XNM_20200621_0_L2A"
    )

    # Construct the `self` link
    feat = {
        "type": "Feature",
        "id": "S2A_11XNM_20200621_0_L2A",
        "collection": "sentinel-s2-l2a",
        "links": [],
    }
    assert stac_accessor(feat) == "S2A_11XNM_20200621_0_L2A"


# The commented out tests work locally but fail during the build because aws creds are not configured
@pytest.mark.parametrize(
    "mosaic_path",
    [
        "file:///path/to/mosaic.json",
        # "dynamodb://us-east-1/amosaic",
        # "s3://mybucket/amosaic.json",
        "https://developmentseed.org/cogeo-mosaic/amosaic.json.gz",  # fake mosaic
    ],
)
def test_mosaic_crud_error(mosaic_path):
    with pytest.raises(MosaicError):
        with MosaicBackend(mosaic_path):
            ...


def test_InMemoryReader():
    """Test MemoryBackend."""
    assets = [asset1, asset2]
    mosaicdef = MosaicJSON.from_urls(assets, quiet=False)

    with MosaicBackend(":memory:", mosaic_def=mosaicdef) as mosaic:
        assert isinstance(mosaic, MemoryBackend)
        assert mosaic.input == ":memory:"
        mosaic.write()
        mosaic._read()

    with MosaicBackend(None, mosaic_def=mosaicdef) as mosaic:
        assert isinstance(mosaic, MemoryBackend)
        assert mosaic.input == ":memory:"

    with MemoryBackend(mosaic_def=mosaicdef) as mosaic:
        (t, _), assets_used = mosaic.tile(150, 182, 9)
        assert t.shape

        (tR, _), assets_usedR = mosaic.tile(150, 182, 9, reverse=True)
        assert tR.shape
        assert not numpy.array_equal(t, tR)

        assert assets_used[0] == assets_usedR[-1]

        with pytest.raises(NoAssetFoundError):
            mosaic.tile(200, 182, 9)

        pts = mosaic.point(-73, 45)
        assert len(pts) == 2
        assert pts[0][0].endswith(".tif")
        assert len(pts[0][1].data) == 3

        ptsR = mosaic.point(-73, 45, reverse=True)
        assert len(ptsR) == 2
        assert ptsR[0][0] == pts[-1][0]

        pts = mosaic.point(-72.5, 46)
        assert len(pts) == 1

        with pytest.raises(PointOutsideBounds):
            mosaic.point(-72.5, 46, allowed_exceptions=None)

        with pytest.raises(NoAssetFoundError):
            mosaic.point(-60, 45)

        assert mosaic.minzoom
        assert mosaic.maxzoom
        assert mosaic.bounds
        assert mosaic.center == mosaicdef.center

        with pytest.raises(NotImplementedError):
            mosaic.preview()

        with pytest.raises(NotImplementedError):
            mosaic.part()

        with pytest.raises(NotImplementedError):
            mosaic.feature()

        info = mosaic.info()
        assert list(info.model_dump()) == [
            "bounds",
            "center",
            "minzoom",
            "maxzoom",
            "name",
            "quadkeys",
            "tilematrixset",
        ]

    mosaic_oneasset = MosaicJSON.from_urls([asset1], quiet=True)
    with MemoryBackend(mosaic_def=mosaic_oneasset) as mosaic:
        assert isinstance(mosaic, MemoryBackend)
        assert len(mosaic.get_assets(150, 182, 9)) == 1
        features = get_footprints([asset2], quiet=True)
        mosaic.update(features)
        assets = mosaic.get_assets(150, 182, 9)
        assert len(assets) == 2
        assert assets[0] == asset2
        assert assets[1] == asset1


def test_sqlite_backend():
    """Test sqlite backend."""
    with MosaicBackend(f"sqlite:///{mosaic_db}:test") as mosaic:
        assert mosaic._backend_name == "SQLite"
        assert isinstance(mosaic, SQLiteBackend)
        assert (
            mosaic.mosaicid == "f7fc24d47a79f1496dcdf9997de83e6305c252a931fba2c7d006b7d8"
        )
        assert mosaic.quadkey_zoom == 7

        info = mosaic.info()
        assert not info.quadkeys
        assert list(info.model_dump()) == [
            "bounds",
            "center",
            "minzoom",
            "maxzoom",
            "name",
            "quadkeys",
            "tilematrixset",
        ]

        info = mosaic.info(quadkeys=True)
        assert info.quadkeys

        assert list(
            mosaic.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}).keys()
        ) == [
            "mosaicjson",
            "name",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.assets_for_tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.assets_for_point(-73, 45) == ["cog1.tif", "cog2.tif"]

        assert len(mosaic.get_assets(150, 182, 9)) == 2
        assert len(mosaic.get_assets(147, 182, 12)) == 0

    # Validation error, mosaic_def is empty
    with pytest.raises(ValidationError):
        with MosaicBackend("sqlite:///:memory::test", mosaic_def={}):
            pass

    # invalid scheme `sqlit://`
    with pytest.raises(ValueError):
        with SQLiteBackend("sqlit:///:memory::test"):
            pass

    # `:` is an invalid character for mosaic name
    with pytest.raises(ValueError):
        with SQLiteBackend("sqlite:///:memory::test:"):
            pass

    # `mosaicjson_metadata` is a reserved mosaic name
    with pytest.raises(AssertionError):
        with MosaicBackend("sqlite:///:memory::mosaicjson_metadata"):
            pass

    # Warns when changing name
    with pytest.warns(UserWarning):
        with MosaicBackend(mosaic_gz) as m:
            with MosaicBackend("sqlite:///:memory::test", mosaic_def=m.mosaic_def) as d:
                assert d.mosaic_def.name == "test"

    # need to set overwrite when mosaic already exists
    with MosaicBackend("sqlite:///:memory::test", mosaic_def=mosaic_content) as mosaic:
        mosaic.write()
        with pytest.raises(MosaicExistsError):
            mosaic.write()
        mosaic.write(overwrite=True)

    # files doesn't exists
    with pytest.raises(MosaicNotFoundError):
        with MosaicBackend("sqlite:///test.db:test2") as mosaic:
            pass

    # mosaic doesn't exists in DB
    with pytest.raises(MosaicNotFoundError):
        with MosaicBackend(f"sqlite:///{mosaic_db}:test2") as mosaic:
            pass

    # Test with `.` in mosaic name
    with pytest.warns(UserWarning):
        with MosaicBackend(
            "sqlite:///:memory::test.mosaic", mosaic_def=mosaic_content
        ) as m:
            m.write()
            assert m._mosaic_exists()
            assert m.mosaic_def.name == "test.mosaic"

            m.delete()
            assert not m._mosaic_exists()
            assert not m._fetch_metadata()

    mosaic_oneasset = MosaicJSON.from_urls([asset1], quiet=True)
    features = get_footprints([asset2], quiet=True)

    # Test update methods
    with MosaicBackend("sqlite:///:memory::test", mosaic_def=mosaic_oneasset) as m:
        m.write()
        meta = m.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"})
        assert len(m.get_assets(150, 182, 9)) == 1

        m.update(features)
        assert not m.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}) == meta

        assets = m.get_assets(150, 182, 9)
        assert len(assets) == 2
        assert assets[0] == asset2
        assert assets[1] == asset1

    # Test update with `add_first=False`
    with MosaicBackend("sqlite:///:memory::test2", mosaic_def=mosaic_oneasset) as m:
        m.write()
        meta = m.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"})
        assert len(m.get_assets(150, 182, 9)) == 1

        m.update(features, add_first=False)
        assert not m.mosaic_def.model_dump(exclude_none=True, exclude={"tiles"}) == meta

        assets = m.get_assets(150, 182, 9)
        assert len(assets) == 2
        assert assets[0] == asset1
        assert assets[1] == asset2

    assert SQLiteBackend.list_mosaics_in_db(mosaic_db) == ["test"]
    assert SQLiteBackend.list_mosaics_in_db(f"sqlite:///{mosaic_db}") == ["test"]

    with pytest.raises(ValueError):
        assert SQLiteBackend.list_mosaics_in_db("test.db")

    # Cannot update a V2 mosaic
    with pytest.raises(AssertionError):
        with MosaicBackend(f"sqlite:///{mosaic_db}:test") as mosaic:
            mosaic.update(features)


def test_tms_and_coordinates():
    """use MemoryBackend for data read tests."""
    assets = [asset1, asset2]
    mosaicdef = MosaicJSON.from_urls(assets, quiet=False)
    with MemoryBackend(mosaic_def=mosaicdef) as mosaic:
        assert mosaic.minzoom == mosaic.mosaic_def.minzoom
        assert mosaic.maxzoom == mosaic.mosaic_def.maxzoom
        tile = mosaic.tms.tile(mosaic.center[0], mosaic.center[1], mosaic.minzoom)
        img, assets = mosaic.tile(*tile)
        assert assets == [asset1, asset2]
        assert img.crs == "epsg:3857"

    tms = morecantile.tms.get("WGS1984Quad")
    with MemoryBackend(mosaic_def=mosaicdef, tms=tms, minzoom=4, maxzoom=7) as mosaic:
        assert mosaic.minzoom == 4
        assert mosaic.maxzoom == 7
        tile = mosaic.tms.tile(mosaic.center[0], mosaic.center[1], mosaic.minzoom)
        img, assets = mosaic.tile(*tile)
        assert assets == [asset1, asset2]
        assert img.crs == "epsg:4326"

    tms = morecantile.tms.get("WebMercatorQuad")
    tms_5041 = morecantile.tms.get("UPSArcticWGS84Quad")
    mosaicdef = MosaicJSON.from_urls(assets, tilematrixset=tms_5041, quiet=True)
    assert mosaicdef.tilematrixset.id == "UPSArcticWGS84Quad"
    with MemoryBackend(mosaic_def=mosaicdef) as mosaic:
        assert mosaic.tms == tms
        assert mosaic.minzoom == tms.minzoom
        assert mosaic.maxzoom == tms.maxzoom


def test_point_crs_coordinates():
    """Test Point with multiple CRS."""
    assets = [asset1, asset2]
    mosaicdef = MosaicJSON.from_urls(assets, quiet=False)
    with MemoryBackend(mosaic_def=mosaicdef) as mosaic:
        pts = mosaic.point(-73, 45)
        assert len(pts) == 2
        assert pts[0][0].endswith(".tif")
        assert len(pts[0][1].data) == 3
        assert pts[0][1].crs == "epsg:4326"
        assert pts[0][1].coordinates == (-73, 45)

        ptsR = mosaic.point(-8200051.8694, 5782905.49327, coord_crs="epsg:3857")
        assert len(ptsR) == 2
        assert ptsR[0][0] == pts[0][0]
        assert ptsR[0][1].crs == "epsg:3857"
        assert ptsR[0][1].coordinates == (-8200051.8694, 5782905.49327)


def test_InMemoryReader_asset_prefix():
    """Test MemoryBackend."""
    assets = [asset1, asset2]
    prefix = os.path.join(os.path.dirname(__file__), "fixtures")
    mosaicdef = MosaicJSON.from_urls(assets, quiet=False, asset_prefix=prefix)

    assert mosaicdef.tiles["0302310"] == ["/cog1.tif", "/cog2.tif"]
    with MemoryBackend(mosaic_def=mosaicdef) as mosaic:
        assets = mosaic.assets_for_tile(150, 182, 9)
        assert assets[0].startswith(prefix)
