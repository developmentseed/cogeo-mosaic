"""cogeo-mosaic AWS S3 backend."""

import json
from typing import Any
from urllib.parse import urlparse

import attr
from boto3.session import Session as boto3_session
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _compress_gz_json, _decompress_gz
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError, MosaicExistsError
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    client: Any = attr.ib(default=None)
    bucket: str = attr.ib(init=False)
    key: str = attr.ib(init=False)

    _backend_name = "AWS S3"

    def __attrs_post_init__(self):
        """Post Init: parse path and create client."""
        parsed = urlparse(self.path)
        self.bucket = parsed.netloc
        self.key = parsed.path.strip("/")
        self.client = self.client or boto3_session().client("s3")
        super().__attrs_post_init__()

    def write(self, overwrite: bool = False, gzip: bool = None, **kwargs: Any):
        """Write mosaicjson document to AWS S3."""
        mosaic_doc = self.mosaic_def.dict(exclude_none=True)
        if gzip or (gzip is None and self.key.endswith(".gz")):
            body = _compress_gz_json(mosaic_doc)
        else:
            body = json.dumps(mosaic_doc).encode("utf-8")

        if not overwrite and _aws_head_object(self.key, self.bucket):
            raise MosaicExistsError("Mosaic file already exist, use `overwrite=True`.")

        _aws_put_data(self.key, self.bucket, body, client=self.client, **kwargs)

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, gzip=None: hashkey(self.path, gzip),
    )
    def _read(self, gzip: bool = None) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        body = _aws_get_data(self.key, self.bucket, client=self.client)

        self._file_byte_size = len(body)

        if gzip or (gzip is None and self.key.endswith(".gz")):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))


def _aws_get_data(key, bucket, client: boto3_session.client = None) -> bytes:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
        raise exc(e.response["Error"]["Message"]) from e

    return response["Body"].read()


def _aws_put_data(
    key: str, bucket: str, body: bytes, client: boto3_session.client = None, **kwargs
) -> str:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    try:
        client.put_object(Bucket=bucket, Key=key, Body=body, **kwargs)
    except ClientError as e:
        status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
        exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
        raise exc(e.response["Error"]["Message"]) from e

    return key


def _aws_head_object(key, bucket, client: boto3_session.client = None) -> bool:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    try:
        return client.head_object(Bucket=bucket, Key=key)
    except ClientError:
        return False
