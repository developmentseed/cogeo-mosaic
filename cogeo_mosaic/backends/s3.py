"""cogeo-mosaic AWS S3 backend."""

from typing import Dict, List, Optional, Union

import json
import functools

import mercantile

from boto3.session import Session as boto3_session

from cogeo_mosaic.model import MosaicJSON
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)


class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    def __init__(
        self,
        bucket: str,
        key: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        client: Optional[boto3_session.client] = None,
    ):
        """Initialize S3Backend."""
        self.client = client or boto3_session().client("s3")
        self.key = key
        self.bucket = bucket

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read()

    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def write(self, gzip=None):
        """Write mosaicjson document to AWS S3."""
        body = dict(self.mosaic_def)
        if gzip or (gzip is None and self.key.endswith(".gz")):
            body = _compress_gz_json(body)
        else:
            body = json.dumps(body).encode("utf-8")

        _aws_put_data(self.key, self.bucket, body, client=self.client)

    def update(self):
        """Update the mosaicjson document."""
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read(self) -> MosaicJSON:
        """Get mosaicjson document."""
        body = _aws_get_data(self.key, self.bucket, client=self.client)

        if self.key.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))


def _aws_get_data(key, bucket, client: boto3_session.client = None) -> bytes:
    if not client:
        session = boto3_session()
        client = session.client("s3")

    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _aws_put_data(
    key: str,
    bucket: str,
    body: bytes,
    options: Dict = {},
    client: boto3_session.client = None,
) -> str:
    if not client:
        session = boto3_session()
        client = session.client("s3")

    client.put_object(Bucket=bucket, Key=key, Body=body, **options)
    return key
