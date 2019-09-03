"""tests cogeo_mosaic.handlers.mosaic."""

import os
import json
import base64

import pytest
from mock import patch

from cogeo_mosaic.handlers.mosaic import app
from cogeo_mosaic.utils import create_mosaic


asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")
mosaic_content = create_mosaic([asset1, asset2])
request_json = os.path.join(os.path.dirname(__file__), "fixtures", "request.json")


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set fake env to make sure we don't hit AWS services."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "jqt")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "rde")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", "/tmp/noconfigheere")
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", "/tmp/noconfighereeither")
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


@pytest.fixture()
def event():
    """Event fixture."""
    return {
        "resource": "/",
        "path": "/",
        "httpMethod": "GET",
        "headers": {"Host": "somewhere-over-the-rainbow.com"},
        "queryStringParameters": {},
    }


def test_favicon(event):
    """Test /favicon.ico route."""
    event["path"] = "/favicon.ico"
    event["httpMethod"] = "GET"

    resp = {
        "body": "",
        "headers": {
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/plain",
        },
        "statusCode": 204,
    }
    res = app(event, {})
    assert res == resp


def test_create_footprint(event):
    """Test /footprint route."""
    event["path"] = "/footprint"
    event["httpMethod"] = "POST"
    event["body"] = base64.b64encode(json.dumps([asset1, asset2]).encode()).decode(
        "utf-8"
    )

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    statusCode = 200

    res = app(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2

    event["path"] = "/footprint"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        body=base64.b64encode(json.dumps([asset1, asset2]).encode()).decode("utf-8")
    )

    res = app(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2


def test_create_mosaic(event):
    """Test /create route."""
    event["path"] = "/create"
    event["httpMethod"] = "POST"
    event["body"] = base64.b64encode(json.dumps([asset1, asset2]).encode()).decode(
        "utf-8"
    )

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET,POST",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    statusCode = 200

    res = app(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body == mosaic_content

    event["path"] = "/create"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        body=base64.b64encode(json.dumps([asset1, asset2]).encode()).decode("utf-8")
    )

    res = app(event, {})
    print(res)
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body == mosaic_content


@patch("cogeo_mosaic.handlers.mosaic.fetch_mosaic_definition")
def test_get_mosaic_info(get_data, event):
    """Test /info route."""
    get_data.return_value = mosaic_content

    event["path"] = "/info"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    statusCode = 200

    res = app(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["bounds"]
    assert body["center"]
    assert body["maxzoom"] == 9
    assert body["minzoom"] == 7
    assert body["name"] == "http://mymosaic.json"
    assert len(body["quadkeys"]) == 9
    assert body["layers"] == ["band1", "band2", "band3"]
    get_data.assert_called_once()
