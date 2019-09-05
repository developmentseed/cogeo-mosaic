"""tests cogeo_mosaic.web."""

import os

import pytest

from cogeo_mosaic.handlers.web import app
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


def test_index(event):
    """Test /index route."""
    event["path"] = "/index.html"
    res = app(event, {})
    assert res["statusCode"] == 200
    assert "https://somewhere-over-the-rainbow.com/tiles/tilejson.json" in res["body"]
    assert "https://somewhere-over-the-rainbow.com/mosaic/info" in res["body"]

    event["path"] = "/"
    res = app(event, {})
    assert res["statusCode"] == 200
    assert "https://somewhere-over-the-rainbow.com/tiles/tilejson.json" in res["body"]
    assert "https://somewhere-over-the-rainbow.com/mosaic/info" in res["body"]


def test_index_create(event):
    """Test /create.html route."""
    event["path"] = "/create.html"
    res = app(event, {})
    assert res["statusCode"] == 200
    assert "https://somewhere-over-the-rainbow.com/mosaic/create" in res["body"]
    assert "https://somewhere-over-the-rainbow.com/mosaic/footprint" in res["body"]
