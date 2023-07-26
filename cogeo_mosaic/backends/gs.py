"""cogeo-mosaic Google Cloud Storage backend."""

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
    from google.auth.exceptions import GoogleAuthError
    from google.cloud.storage import Client as gcp_session
except ImportError:  # pragma: nocover
    gcp_session = None  # type: ignore
    GoogleAuthError = None  # type: ignore


@attr.s
class GCSBackend(BaseBackend):
    """GCS Backend Adapter"""

    client: Any = attr.ib(default=None)
    bucket: str = attr.ib(init=False)
    key: str = attr.ib(init=False)

    _backend_name = "Google Cloud Storage"

    def __attrs_post_init__(self):
        """Post Init: parse path and create client."""
        assert (
            gcp_session is not None
        ), "'google-cloud-storage' must be installed to use GCSBackend"

        parsed = urlparse(self.input)
        self.bucket = parsed.netloc
        self.key = parsed.path.strip("/")
        self.client = self.client or gcp_session()
        super().__attrs_post_init__()

    def write(self, overwrite: bool = False, **kwargs: Any):
        """Write mosaicjson document to Google Cloud Storage."""
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
            gcs_bucket = self.client.bucket(bucket)
            response = gcs_bucket.blob(key).download_as_bytes()
        except GoogleAuthError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e

        return response

    def _put_object(self, key: str, bucket: str, body: bytes, **kwargs) -> str:
        try:
            gcs_bucket = self.client.bucket(bucket)
            blob = gcs_bucket.blob(key)
            blob.upload_from_string(body)
        except GoogleAuthError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e

        return key

    def _head_object(self, key: str, bucket: str) -> bool:
        try:
            gcs_bucket = self.client.bucket(bucket)
            blob = gcs_bucket.blob(key)
            return blob.exists()
        except GoogleAuthError:
            return False
