"""cogeo_mosaic.backends."""

from typing import Any
from urllib.parse import urlparse

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.http import HttpBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.stac import STACBackend


def MosaicBackend(url: str, *args: Any, **kwargs: Any) -> BaseBackend:
    """Select mosaic backend for url."""
    parsed = urlparse(url)

    if parsed.scheme and parsed.scheme.startswith("stac+"):
        url = url.replace("stac+", "")
        return STACBackend(url, *args, **kwargs)

    if parsed.scheme == "s3":
        return S3Backend(url, *args, **kwargs)

    if parsed.scheme == "dynamodb":
        return DynamoDBBackend(url, *args, **kwargs)

    if parsed.scheme in ["https", "http"]:
        return HttpBackend(url, *args, **kwargs)

    if parsed.scheme == "file":
        path = parsed.path
        return FileBackend(path, *args, **kwargs)

    return FileBackend(url, *args, **kwargs)
