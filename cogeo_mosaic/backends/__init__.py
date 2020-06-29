"""cogeo_mosaic.backends."""

from urllib.parse import urlparse

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.http import HttpBackend
from cogeo_mosaic.backends.s3 import S3Backend


def MosaicBackend(url: str, **kwargs) -> BaseBackend:
    """Select mosaic backend for url."""
    parsed = urlparse(url)

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.strip("/")
        return S3Backend(bucket, key, **kwargs)

    if parsed.scheme == "dynamodb":
        table_name = parsed.path.strip("/")
        region = parsed.netloc
        if region:
            kwargs.update(dict(region=region))
        return DynamoDBBackend(table_name, **kwargs)

    if parsed.scheme in ["https", "http"]:
        return HttpBackend(url, **kwargs)

    if parsed.scheme == "file":
        path = parsed.path
        return FileBackend(path, **kwargs)

    return FileBackend(url, **kwargs)
