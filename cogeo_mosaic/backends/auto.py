"""
cogeo_mosaic.backend.auto: Automatically select backend from url

This is in a separate module to prevent circular imports
"""

from urllib.parse import urlparse

from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.http import HttpBackend
from cogeo_mosaic.backends.s3 import S3Backend


def MosaicBackend(url: str, **kwargs):
    parsed = urlparse(url)

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.strip("/")
        return S3Backend(bucket=bucket, key=key, **kwargs)

    if parsed.scheme == "dynamodb":
        table_name = parsed.path.strip("/")
        region = parsed.netloc
        if region:
            return DynamoDBBackend(table_name=table_name, region=region, **kwargs)

        return DynamoDBBackend(table_name=table_name, **kwargs)

    if parsed.scheme in ["https", "http", "ftp"]:
        return HttpBackend(url=url, **kwargs)

    if parsed.scheme == "file":
        path = parsed.path
        return FileBackend(path=path, **kwargs)

    return FileBackend(path=url, **kwargs)
