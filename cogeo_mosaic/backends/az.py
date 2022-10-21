"""cogeo-mosaic Azure Blob Storage backend."""

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
    from azure.core.exceptions import HttpResponseError
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
except ImportError:
    HttpResponseError = None
    DefaultAzureCredential = None
    BlobServiceClient = None


@attr.s
class ABSBackend(BaseBackend):
    """Azure Blob Storage Backend Adapter"""

    client: Any = attr.ib(default=None)
    account_url: str = attr.ib(init=False)
    container: str = attr.ib(init=False)
    key: str = attr.ib(init=False)

    _backend_name = "Azure Blob Storage"

    def __attrs_post_init__(self):
        """Post Init: parse path and create client."""
        assert (
            HttpResponseError is not None
        ), "'azure-identity' and 'azure-storage-blob' must be installed to use ABSBackend"

        az_credentials = DefaultAzureCredential()

        parsed = urlparse(self.input)
        self.account_url = "https://%s" % parsed.netloc
        self.container = parsed.path.split("/")[1]
        self.key = parsed.path.strip("/%s" % self.container)
        self.client = self.client or BlobServiceClient(
            account_url=self.account_url, credential=az_credentials
        )
        super().__attrs_post_init__()

    def write(self, overwrite: bool = False, **kwargs: Any):
        """Write mosaicjson document to Azure Blob Storage."""
        if not overwrite and self._head_object(self.key, self.container):
            raise MosaicExistsError("Mosaic file already exist, use `overwrite=True`.")

        mosaic_doc = self.mosaic_def.dict(exclude_none=True)
        if self.key.endswith(".gz"):
            body = _compress_gz_json(mosaic_doc)
        else:
            body = json.dumps(mosaic_doc).encode("utf-8")

        self._put_object(self.key, self.container, body, **kwargs)

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.input),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        body = self._get_object(self.key, self.container)
        self._file_byte_size = len(body)

        if self.key.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))

    def _get_object(self, key: str, container: str) -> bytes:
        try:
            container_client = self.client.get_container_client(container)
            blob_client = container_client.get_blob_client(key)
            response = blob_client.download_blob().readall()
        except HttpResponseError as e:
            exc = _HTTP_EXCEPTIONS.get(e.status_code, MosaicError)
            raise exc(e.reason) from e

        return response

    def _put_object(self, key: str, container: str, body: bytes, **kwargs) -> str:
        try:
            container_client = self.client.get_container_client(container)
            blob_client = container_client.get_blob_client(key)
            blob_client.upload_blob(body)
        except HttpResponseError as e:
            exc = _HTTP_EXCEPTIONS.get(e.status_code, MosaicError)
            raise exc(e.reason) from e

        return key

    def _head_object(self, key: str, container: str) -> bool:
        try:
            container_client = self.client.get_container_client(container)
            blob_client = container_client.get_blob_client(key)
            return blob_client.exists()
        except HttpResponseError:
            return False
