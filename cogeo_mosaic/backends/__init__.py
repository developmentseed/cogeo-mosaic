"""cogeo_mosaic.backends."""

from typing import Any
from urllib.parse import parse_qsl, urlparse

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.sqlite import SQLiteBackend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.web import HttpBackend


def MosaicBackend(url: str, *args: Any, **kwargs: Any) -> BaseBackend:
    """Select mosaic backend for url."""
    parsed = urlparse(url)

    # `stac+https//{hostname}/key`
    if parsed.scheme and parsed.scheme.startswith("stac+"):
        url = url.replace("stac+", "")
        return STACBackend(url, *args, **kwargs)

    # `s3:///{bucket}{key}`
    elif parsed.scheme == "s3":
        return S3Backend(url, *args, **kwargs)

    # `dynamodb://{region}/{table}:{mosaic}`
    elif parsed.scheme == "dynamodb":
        return DynamoDBBackend(url, *args, **kwargs)

    # `sqlite:///{path.db}?mosaic={mosaic}`
    elif parsed.scheme == "sqlite":
        db_path = parsed.path[1:]
        qs = dict(parse_qsl(parsed.query))
        if "mosaic" not in qs:
            raise ValueError("missing `mosaic` parameter in URI.")

        return SQLiteBackend(db_path, qs["mosaic"], *args, **kwargs)

    # https://{hostname}/{path}
    elif parsed.scheme in ["https", "http"]:
        return HttpBackend(url, *args, **kwargs)

    # file://{path}
    elif parsed.scheme == "file":
        path = parsed.path
        return FileBackend(path, *args, **kwargs)

    elif parsed.scheme:
        raise ValueError(f"'{parsed.scheme}' is not supported")

    # fallback to FileBackend
    else:
        return FileBackend(url, *args, **kwargs)
