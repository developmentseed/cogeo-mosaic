"""cogeo-mosaic AWS S3 backend."""

import json
from typing import Any, Dict, List, Optional, Union

import mercantile
from boto3.session import Session as boto3_session
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError
from cogeo_mosaic.mosaic import MosaicJSON


class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    _backend_name = "AWS S3"

    def __init__(
        self,
        bucket: str,
        key: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        client: Optional[boto3_session.client] = None,
        **kwargs: Any,
    ):
        """Initialize S3Backend."""
        self.client = client or boto3_session().client("s3")
        self.key = key
        self.bucket = bucket
        self.path = f"s3://{bucket}/{key}"

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self._read(**kwargs)

    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self, gzip: bool = None, **kwargs: Any):
        """Write mosaicjson document to AWS S3."""
        mosaic_doc = self.mosaic_def.dict(exclude_none=True)
        if gzip or (gzip is None and self.key.endswith(".gz")):
            body = _compress_gz_json(mosaic_doc)
        else:
            body = json.dumps(mosaic_doc).encode("utf-8")

        _aws_put_data(self.key, self.bucket, body, client=self.client, **kwargs)

    @cached(
        TTLCache(maxsize=512, ttl=300),
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
