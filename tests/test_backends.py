"""Test backends."""

import json
import os
import time
from decimal import Decimal
from io import BytesIO
from typing import Dict, List
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.http import HttpBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.stac import _fetch as stac_search
from cogeo_mosaic.backends.stac import default_stac_accessor as stac_accessor
from cogeo_mosaic.backends.utils import _decompress_gz
from cogeo_mosaic.mosaic import MosaicJSON

mosaic_gz = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
mosaic_bin = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.bin")
mosaic_json = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
mosaic_jsonV1 = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic_0.0.1.json")
stac_page1 = os.path.join(os.path.dirname(__file__), "fixtures", "stac_p1.geojson")
stac_page2 = os.path.join(os.path.dirname(__file__), "fixtures", "stac_p2.geojson")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())


def test_file_backend():
    """Test File backend."""
    with MosaicBackend(mosaic_gz) as mosaic:
        assert mosaic._backend_name == "File"
        assert isinstance(mosaic, FileBackend)
        assert (
            mosaic.mosaicid
            == "f39f05644731addf1d183fa094ff6478900a27912ad035ef570231b1"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.point(-73, 45) == ["cog1.tif", "cog2.tif"]

    with MosaicBackend(mosaic_bin, gzip=True) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert (
            mosaic.mosaicid
            == "f39f05644731addf1d183fa094ff6478900a27912ad035ef570231b1"
        )
        assert mosaic.quadkey_zoom == 7

    with MosaicBackend(mosaic_json) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert mosaic.quadkey_zoom == 7

    with MosaicBackend(mosaic_jsonV1) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert mosaic.quadkey_zoom == 7
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "bounds",
            "center",
        ]

    runner = CliRunner()
    with runner.isolated_filesystem():
        with MosaicBackend("mosaic.json", mosaic_def=mosaic_content) as mosaic:
            mosaic.write()
            with open("mosaic.json") as f:
                m = json.loads(f.read())
                print
                assert m["quadkey_zoom"] == 7

        with MosaicBackend("mosaic.json.gz", mosaic_def=mosaic_content) as mosaic:
            mosaic.write()
            with open("mosaic.json.gz", "rb") as f:
                m = json.loads(_decompress_gz(f.read()))
                assert m["quadkey_zoom"] == 7

        with MosaicBackend("abinaryfile.bin", mosaic_def=mosaic_content) as mosaic:
            mosaic.write(gzip=True)
            with open("abinaryfile.bin", "rb") as f:
                m = json.loads(_decompress_gz(f.read()))
                assert m["quadkey_zoom"] == 7


class MockResponse:
    def __init__(self, data):
        self.data = data

    @property
    def content(self):
        return self.data


@patch("cogeo_mosaic.backends.http.requests")
def test_http_backend(requests):
    """Test HTTP backend."""
    with open(mosaic_json, "r") as f:
        requests.get.return_value = MockResponse(f.read())

    with MosaicBackend("https://mymosaic.json") as mosaic:
        assert mosaic._backend_name == "HTTP"
        assert isinstance(mosaic, HttpBackend)
        assert (
            mosaic.mosaicid
            == "f39f05644731addf1d183fa094ff6478900a27912ad035ef570231b1"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.point(-73, 45) == ["cog1.tif", "cog2.tif"]
    requests.get.assert_called_once()
    requests.mock_reset()

    with open(mosaic_json, "r") as f:
        requests.get.return_value = MockResponse(f.read())

    with pytest.raises(NotImplementedError):
        with MosaicBackend("https://mymosaic.json") as mosaic:
            mosaic.update()
        requests.get.assert_called_once()
        requests.mock_reset()

    with pytest.raises(NotImplementedError):
        with MosaicBackend(
            "https://mymosaic.json", mosaic_def=mosaic_content
        ) as mosaic:
            mosaic.write()
        requests.get.assert_not_called()
        requests.mock_reset()

    with open(mosaic_gz, "rb") as f:
        requests.get.return_value = MockResponse(f.read())

    with MosaicBackend("https://mymosaic.json.gz") as mosaic:
        assert isinstance(mosaic, HttpBackend)
        assert (
            mosaic.mosaicid
            == "f39f05644731addf1d183fa094ff6478900a27912ad035ef570231b1"
        )


@patch("cogeo_mosaic.backends.s3.boto3_session")
def test_s3_backend(session):
    """Test S3 backend."""
    with open(mosaic_gz, "rb") as f:
        session.return_value.client.return_value.get_object.return_value = {
            "Body": BytesIO(f.read())
        }
    session.return_value.client.return_value.put_object.return_value = True

    with MosaicBackend("s3://mybucket/mymosaic.json.gz") as mosaic:
        assert mosaic._backend_name == "AWS S3"
        assert isinstance(mosaic, S3Backend)
        assert (
            mosaic.mosaicid
            == "f39f05644731addf1d183fa094ff6478900a27912ad035ef570231b1"
        )
        assert mosaic.quadkey_zoom == 7
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.point(-73, 45) == ["cog1.tif", "cog2.tif"]
        session.return_value.client.return_value.get_object.assert_called_once_with(
            Bucket="mybucket", Key="mymosaic.json.gz"
        )
        session.return_value.client.return_value.put_object.assert_not_called()
        session.reset_mock()

    with open(mosaic_gz, "rb") as f:
        session.return_value.client.return_value.get_object.return_value = {
            "Body": BytesIO(f.read())
        }
    session.return_value.client.return_value.put_object.return_value = True

    with MosaicBackend(
        "s3://mybucket/mymosaic.json.gz", mosaic_def=mosaic_content
    ) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    kwargs = session.return_value.client.return_value.put_object.call_args[1]
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "mymosaic.json.gz"
    assert MosaicJSON(**json.loads(_decompress_gz(kwargs["Body"])))
    session.reset_mock()

    with MosaicBackend("s3://mybucket/00000", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write(gzip=True)
    session.return_value.client.return_value.get_object.assert_not_called()
    kwargs = session.return_value.client.return_value.put_object.call_args[1]
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "00000"
    assert MosaicJSON(**json.loads(_decompress_gz(kwargs["Body"])))
    session.reset_mock()

    with MosaicBackend("s3://mybucket/00000", mosaic_def=mosaic_content) as mosaic:
        assert isinstance(mosaic, S3Backend)
        mosaic.write()
    session.return_value.client.return_value.get_object.assert_not_called()
    kwargs = session.return_value.client.return_value.put_object.call_args[1]
    assert kwargs["Bucket"] == "mybucket"
    assert kwargs["Key"] == "00000"
    assert MosaicJSON(**json.loads(kwargs["Body"]))
    session.reset_mock()


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

    def get_item(self, Key: Dict = {}) -> Dict:
        """Mock Get Item."""
        quadkey = Key["quadkey"]
        if quadkey == "-1":
            return {
                "Item": {
                    "mosaicjson": "0.0.2",
                    "version": "1.0.0",
                    "minzoom": 7,
                    "maxzoom": 9,
                    "quadkey_zoom": 7,
                    "bounds": [
                        Decimal("-75.98703377403767"),
                        Decimal("44.93504283303786"),
                        Decimal("-71.337604724099"),
                        Decimal("47.096855991923235"),
                    ],
                    "center": [Decimal("-74.53125"), Decimal("45.99569351896393"), 7],
                }
            }

        items = mosaic_content["tiles"].get(quadkey)
        if not items:
            return {}
        return {"Item": {"assets": items}}


@patch("cogeo_mosaic.backends.dynamodb.boto3.resource")
def test_dynamoDB_backend(client):
    """Test DynamoDB backend."""
    client.return_value.Table = MockTable

    with MosaicBackend("dynamodb:///thiswaskylebarronidea") as mosaic:
        assert mosaic._backend_name == "AWS DynamoDB"
        assert isinstance(mosaic, DynamoDBBackend)
        assert mosaic.quadkey_zoom == 7
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.tile(150, 182, 9) == ["cog1.tif", "cog2.tif"]
        assert mosaic.point(-73, 45) == ["cog1.tif", "cog2.tif"]

    with MosaicBackend(
        "dynamodb:///thiswaskylebarronidea", mosaic_def=mosaic_content
    ) as mosaic:
        assert isinstance(mosaic, DynamoDBBackend)
        items = mosaic._create_items()
        assert len(items) == 10
        assert items[-1] == {"quadkey": "0302330", "assets": ["cog1.tif", "cog2.tif"]}
        mosaic._create_table()


class STACMockResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


@patch("cogeo_mosaic.backends.stac.requests.post")
def test_stac_backend(post):
    """Test STAC backend."""
    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend("https://a_stac.api/search", {}, 8, 14, max_items=8) as mosaic:
        assert mosaic._backend_name == "STAC"
        assert isinstance(mosaic, STACBackend)
        assert post.call_count == 1
        assert mosaic.quadkey_zoom == 8
        assert list(mosaic.metadata.keys()) == [
            "mosaicjson",
            "version",
            "minzoom",
            "maxzoom",
            "quadkey_zoom",
            "bounds",
            "center",
        ]
        assert mosaic.tile(210, 90, 10) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
        assert mosaic.point(-106.050, 81.43) == [
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_12XWR_20200621_0_L2A",
            "https://earth-search.aws.element84.com/v0/collections/sentinel-s2-l2a/items/S2A_13XDL_20200621_0_L2A",
        ]
    post.reset_mock()

    with open(stac_page1, "r") as f1, open(stac_page2, "r") as f2:
        post.side_effect = [
            STACMockResponse(json.loads(f1.read())),
            STACMockResponse(json.loads(f2.read())),
        ]

    with STACBackend("https://a_stac.api/search", {}, 8, 14, max_items=15) as mosaic:
        assert mosaic._backend_name == "STAC"
        assert isinstance(mosaic, STACBackend)
        assert post.call_count == 2
        assert mosaic.quadkey_zoom == 8
        assert list(mosaic.metadata.keys()) == [
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

    with STACBackend("https://a_stac.api/search", {}, 8, 14, max_items=15) as mosaic:
        with pytest.raises(NotImplementedError):
            mosaic.write()

        with pytest.raises(NotImplementedError):
            mosaic.update()


@patch("cogeo_mosaic.backends.stac.requests.post")
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
