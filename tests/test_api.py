"""tests ard_tiler.api."""

import os
import json
import base64

import pytest
from mock import patch

from cogeo_mosaic.handlers.api import APP
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
        "path": "/",
        "httpMethod": "GET",
        "headers": {},
        "queryStringParameters": {},
    }


def test_API_favicon(event):
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
    res = APP(event, {})
    assert res == resp


def test_create_footprint(event):
    """Test /create_mosaic route."""
    event["path"] = "/create_footprint"
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

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2

    event["path"] = "/create_footprint"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        body=base64.b64encode(json.dumps([asset1, asset2]).encode()).decode("utf-8")
    )

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2


def test_create_mosaic(event):
    """Test /create_mosaic route."""
    event["path"] = "/create_mosaic"
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

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body == mosaic_content

    event["path"] = "/create_mosaic"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        body=base64.b64encode(json.dumps([asset1, asset2]).encode()).decode("utf-8")
    )

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body == mosaic_content


@patch("cogeo_mosaic.handlers.api.fetch_mosaic_definition")
def test_get_mosaic_info(get_data, event):
    """Test /mosaic/info route."""
    get_data.return_value = mosaic_content

    event["path"] = "/mosaic/info"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    statusCode = 200

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["bounds"]
    assert body["center"]
    assert body["maxzoom"] == 9
    assert body["minzoom"] == 7
    assert body["name"] == "mymosaic.json"
    assert len(body["quadkeys"]) == 9
    assert body["layers"] == ["band1", "band2", "band3"]
    get_data.assert_called_once()


@patch("cogeo_mosaic.handlers.api.fetch_mosaic_definition")
def test_tilejson(get_data, event):
    """Test /mosaic/tilejson.json route."""
    get_data.return_value = mosaic_content

    with open(request_json, "r") as f:
        event = json.loads(f.read())

    event["path"] = "/mosaic/tilejson.json"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json", rescale="-1,1")

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }
    statusCode = 200

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["bounds"]
    assert body["center"]
    assert body["maxzoom"] == 9
    assert body["minzoom"] == 7
    assert body["name"] == "mymosaic.json"
    assert body["tilejson"] == "2.1.0"
    assert body["tiles"]
    get_data.assert_called_once()


@patch("cogeo_mosaic.handlers.api.get_assets")
def test_API_errors(get_assets, event):
    """Test /tiles route."""
    get_assets.return_value = []

    # missing URL
    event["path"] = f"/mosaic/9/150/182.png"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 400
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "Missing 'URL' parameter"

    # empty assets
    event["path"] = f"/mosaic/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 204
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "No assets found for tile 9-150-182"


@patch("cogeo_mosaic.handlers.api.get_assets")
def test_API_tiles(get_assets, event):
    """Test /tiles route."""
    get_assets.return_value = [asset1, asset2]

    # empty assets
    event["path"] = f"/mosaic/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    # empty assets
    event["path"] = f"/mosaic/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", rescale="0,10000", indexes="1", color_map="cfastie"
    )
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]


@patch("cogeo_mosaic.handlers.api.get_assets")
def test_API_emptytiles(get_assets, event):
    """Test /tiles route."""
    get_assets.return_value = [asset1, asset2]

    # empty assets
    event["path"] = f"/mosaic/9/140/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 204
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "empty tiles"
