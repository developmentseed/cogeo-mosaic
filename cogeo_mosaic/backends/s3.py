"""cogeo-mosaic AWS S3 backend."""

import json
from typing import Any
from urllib.parse import urlparse

import attr
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _compress_gz_json, _decompress_gz
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError, MosaicExistsError
from cogeo_mosaic.mosaic import MosaicJSON

try:
    from boto3.session import Session as boto3_session
    from botocore.exceptions import ClientError
except ImportError:  # pragma: nocover
    boto3_session = None  # type: ignore
    ClientError = None  # type: ignore


@attr.s
class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    client: Any = attr.ib(default=None)
    bucket: str = attr.ib(init=False)
    key: str = attr.ib(init=False)

    _backend_name = "AWS S3"

    def __attrs_post_init__(self):
        """Post Init: parse path and create client."""
        assert boto3_session is not None, "'boto3' must be installed to use S3Backend"

        parsed = urlparse(self.input)
        self.bucket = parsed.netloc
        self.key = parsed.path.strip("/")
        self.client = self.client or boto3_session().client("s3")
        super().__attrs_post_init__()

    def write(self, overwrite: bool = False, **kwargs: Any):
        """Write mosaicjson document to AWS S3."""
        if not overwrite and self._head_object(self.key, self.bucket):
            raise MosaicExistsError("Mosaic file already exist, use `overwrite=True`.")

        mosaic_doc = self.mosaic_def.model_dump_json(exclude_none=True)
        if self.key.endswith(".gz"):
            body = _compress_gz_json(mosaic_doc)
        else:
            body = mosaic_doc.encode("utf-8")

        self._put_object(self.key, self.bucket, body, **kwargs)

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.input),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        body = self._get_object(self.key, self.bucket)

        self._file_byte_size = len(body)

        if self.key.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))

    def _get_object(self, key: str, bucket: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=bucket, Key=key)
        except ClientError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e

        return response["Body"].read()

    def _put_object(self, key: str, bucket: str, body: bytes, **kwargs) -> str:
        try:
            self.client.put_object(Bucket=bucket, Key=key, Body=body, **kwargs)
        except ClientError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e

        return key

    def _head_object(self, key: str, bucket: str) -> bool:
        try:
            return self.client.head_object(Bucket=bucket, Key=key)
        except ClientError:
            return False
