"""cogeo_mosaic.backends."""

from typing import Any
from urllib.parse import urlparse

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.memory import MemoryBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.sqlite import SQLiteBackend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.web import HttpBackend


def MosaicBackend(url: str, *args: Any, **kwargs: Any) -> BaseBackend:
    """Select mosaic backend for url."""
    parsed = urlparse(url)

    if not url or url == ":memory:":
        return MemoryBackend(*args, **kwargs)

    # `stac+https//{hostname}/{path}`
    elif parsed.scheme and parsed.scheme.startswith("stac+"):
        url = url.replace("stac+", "")
        return STACBackend(url, *args, **kwargs)

    # `s3:///{bucket}{key}`
    elif parsed.scheme == "s3":
        return S3Backend(url, *args, **kwargs)

    # `dynamodb://{region}/{table}:{mosaic}`
    elif parsed.scheme == "dynamodb":
        return DynamoDBBackend(url, *args, **kwargs)

    # `sqlite:///{path.db}:{mosaic}`
    elif parsed.scheme == "sqlite":
        return SQLiteBackend(url, *args, **kwargs)

    # https://{hostname}/{path}
    elif parsed.scheme in ["https", "http"]:
        return HttpBackend(url, *args, **kwargs)

    # file:///{path}
    elif parsed.scheme == "file":
        return FileBackend(parsed.path, *args, **kwargs)

    # Invalid Scheme
    elif parsed.scheme:
        raise ValueError(f"'{parsed.scheme}' is not supported")

    # fallback to FileBackend
    else:
        return FileBackend(url, *args, **kwargs)
