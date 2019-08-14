"""tests ard_tiler.api."""

import os
import json
import base64
import urllib

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
        "resource": "/",
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

    res = APP(event, {})
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

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = json.loads(res["body"])
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 2


def test_create_mosaic(event):
    """Test /mosaic route."""
    event["path"] = "/mosaic"
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

    event["path"] = "/mosaic"
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
def test_get_mosaic_wmts(get_data):
    """Test /wmts route."""
    get_data.return_value = mosaic_content

    event = {
        "resource": "/{proxy+}",
        "pathParameters": {"proxy": "wmts"},
        "path": "/wmts",
        "headers": {"host": "afakeapi.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {"stage": "production"},
    }

    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(tile_scale="2", url="http://mymosaic.json")

    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/xml",
    }
    statusCode = 200

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == statusCode
    body = res["body"]
    assert (
        "https://afakeapi.execute-api.us-east-1.amazonaws.com/production/wmts" in body
    )
    get_data.assert_called_once()


@patch("cogeo_mosaic.handlers.api.fetch_mosaic_definition")
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
    """Test /tilejson.json route."""
    get_data.return_value = mosaic_content

    event = {
        "resource": "/{proxy+}",
        "pathParameters": {"proxy": "tilejson.json"},
        "path": "/tilejson.json",
        "headers": {"host": "afakeapi.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {"stage": "production"},
    }
    event["path"] = "/tilejson.json"
    event["httpMethod"] = "GET"
    headers = {
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json",
    }

    # png 256px
    event["queryStringParameters"] = dict(url="http://mymosaic.json", rescale="-1,1")

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    assert body["bounds"]
    assert body["center"]
    assert body["maxzoom"] == 9
    assert body["minzoom"] == 7
    assert body["name"] == "mymosaic.json"
    assert body["tilejson"] == "2.1.0"

    url_info = urllib.parse.urlparse(body["tiles"][0])
    assert url_info.netloc == "afakeapi.execute-api.us-east-1.amazonaws.com"
    assert url_info.path == "/production/{z}/{x}/{y}@1x.png"
    qs = urllib.parse.parse_qs(url_info.query)
    assert qs["url"][0] == "http://mymosaic.json"
    assert qs["rescale"][0] == "-1,1"

    # Jpeg 512px
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", tile_format="jpg", tile_scale=2
    )

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    url_info = urllib.parse.urlparse(body["tiles"][0])
    assert url_info.netloc == "afakeapi.execute-api.us-east-1.amazonaws.com"
    assert url_info.path == "/production/{z}/{x}/{y}@2x.jpg"
    qs = urllib.parse.parse_qs(url_info.query)
    assert qs["url"][0] == "http://mymosaic.json"

    event["queryStringParameters"] = dict(url="http://mymosaic.json", tile_format="pbf")

    res = APP(event, {})
    assert res["headers"] == headers
    assert res["statusCode"] == 200
    body = json.loads(res["body"])
    url_info = urllib.parse.urlparse(body["tiles"][0])
    assert url_info.netloc == "afakeapi.execute-api.us-east-1.amazonaws.com"
    assert url_info.path == "/production/{z}/{x}/{y}.pbf"
    qs = urllib.parse.parse_qs(url_info.query)
    assert qs["url"][0] == "http://mymosaic.json"


@patch("cogeo_mosaic.handlers.api.fetch_and_find_assets")
def test_API_errors(get_assets, event):
    """Test /tiles routes."""
    get_assets.return_value = []

    # missing URL
    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    res = APP(event, {})
    assert res["statusCode"] == 400
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "Missing 'URL' parameter"

    # empty assets
    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 204
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "No assets found for tile 9-150-182"


@patch("cogeo_mosaic.handlers.api.fetch_and_find_assets")
def test_API_tiles(get_assets, event):
    """Test /tiles routes."""
    get_assets.return_value = [asset1, asset2]

    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", pixel_selection="first"
    )
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", pixel_selection="highest"
    )
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", pixel_selection="lowest"
    )
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    # See https://github.com/cogeotiff/rio-tiler-mosaic/issues/4
    # event["path"] = f"/9/150/182.png"
    # event["httpMethod"] = "GET"
    # event["queryStringParameters"] = dict(
    #     url="http://mymosaic.json", pixel_selection="mean"
    # )
    # res = APP(event, {})
    # assert res["statusCode"] == 200
    # headers = res["headers"]
    # assert headers["Content-Type"] == "image/png"
    # assert res["body"]

    # event["path"] = f"/9/150/182.png"
    # event["httpMethod"] = "GET"
    # event["queryStringParameters"] = dict(
    #     url="http://mymosaic.json", pixel_selection="median"
    # )
    # res = APP(event, {})
    # assert res["statusCode"] == 200
    # headers = res["headers"]
    # assert headers["Content-Type"] == "image/png"
    # assert res["body"]

    event["path"] = f"/9/150/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(
        url="http://mymosaic.json", rescale="0,10000", indexes="1", color_map="cfastie"
    )
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]

    event["path"] = f"/9/150/182@2x.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json", rescale="0,10000")
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "image/png"
    assert res["body"]


@patch("cogeo_mosaic.handlers.api.fetch_and_find_assets")
def test_API_emptytiles(get_assets, event):
    """Test /tiles routes."""
    get_assets.return_value = [asset1, asset2]

    # empty assets
    event["path"] = f"/9/140/182.png"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 204
    headers = res["headers"]
    assert headers["Content-Type"] == "text/plain"
    assert res["body"] == "empty tiles"


@patch("cogeo_mosaic.handlers.api.fetch_and_find_assets")
def test_API_MVTtiles(get_assets, event):
    """Test /tiles routes."""
    get_assets.return_value = [asset1, asset2]

    event["path"] = f"/9/150/182.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = {}
    res = APP(event, {})
    assert res["statusCode"] == 500

    event["path"] = f"/9/150/182.pbf"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json", tile_size="64")
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]

    event["path"] = f"/9/150/182.mvt"
    event["httpMethod"] = "GET"
    event["queryStringParameters"] = dict(url="http://mymosaic.json")
    res = APP(event, {})
    assert res["statusCode"] == 200
    headers = res["headers"]
    assert headers["Content-Type"] == "application/x-protobuf"
    assert res["body"]
