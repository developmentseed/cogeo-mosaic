"""cogeo_mosaic.backends."""

from typing import Any
from urllib.parse import urlparse

from cogeo_mosaic.backends.az import ABSBackend
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.gs import GCSBackend
from cogeo_mosaic.backends.memory import MemoryBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.sqlite import SQLiteBackend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.web import HttpBackend


def MosaicBackend(input: str, *args: Any, **kwargs: Any) -> BaseBackend:  # noqa: C901
    """Select mosaic backend for input."""
    parsed = urlparse(input)

    if not input or input == ":memory:":
        return MemoryBackend(*args, **kwargs)

    # `stac+https//{hostname}/{path}`
    elif parsed.scheme and parsed.scheme.startswith("stac+"):
        input = input.replace("stac+", "")
        return STACBackend(input, *args, **kwargs)

    # `s3:///{bucket}{key}`
    elif parsed.scheme == "s3":
        return S3Backend(input, *args, **kwargs)

    # `gs://{bucket}/{key}`
    elif parsed.scheme == "gs":
        return GCSBackend(input, *args, **kwargs)

    # `az://{storageaccount}.blob.core.windows.net/{container}/{key}`
    elif parsed.scheme == "az":
        return ABSBackend(input, *args, **kwargs)

    # `dynamodb://{region}/{table}:{mosaic}`
    elif parsed.scheme == "dynamodb":
        return DynamoDBBackend(input, *args, **kwargs)

    # `sqlite:///{path.db}:{mosaic}`
    elif parsed.scheme == "sqlite":
        return SQLiteBackend(input, *args, **kwargs)

    # https://{hostname}/{path}
    elif parsed.scheme in ["https", "http"]:
        return HttpBackend(input, *args, **kwargs)

    # file:///{path}
    elif parsed.scheme == "file":
        return FileBackend(parsed.path, *args, **kwargs)

    # Invalid Scheme
    elif parsed.scheme:
        raise ValueError(f"'{parsed.scheme}' is not supported")

    # fallback to FileBackend
    else:
        return FileBackend(input, *args, **kwargs)
