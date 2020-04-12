import functools
import json
from typing import BinaryIO, Dict, Optional, Tuple

import mercantile
from boto3.session import Session as boto3_session
from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)


class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    def __init__(
        self,
        bucket: str,
        key: Optional[str] = None,
        mode: str = 'r',
        client: boto3_session.client = None,
    ):
        if client:
            self.client = client
        else:
            self.client = boto3_session().client("s3")

        self.key = key
        self.bucket = bucket
        self.mosaic_def = None
        if 'r' in mode:
            self.mosaic_def = self.read_mosaic(bucket, key)

    def tile(self, x: int, y: int, z: int, bucket: str, key: str) -> Tuple[str]:
        """Retrieve assets for tile."""

        return get_assets_from_json(
            self.mosaic_def["tiles"], self.quadkey_zoom, x, y, z
        )

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""

        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def["tiles"], self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def upload(self, mosaic: Dict):
        key = f"mosaics/{self.mosaicid}.json.gz"
        _aws_put_data(key, self.bucket, _compress_gz_json(mosaic), client=self.client)

    @functools.lru_cache(maxsize=512)
    def read_mosaic(self, bucket: str, key: str) -> Dict:
        """Get Mosaic definition info."""

        body = _aws_get_data(key, bucket, client=self.client)

        if key.endswith(".gz"):
            body = _decompress_gz(body)

        return json.loads(body)


def _aws_get_data(key, bucket, client: boto3_session.client = None) -> BinaryIO:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()


def _aws_put_data(
    key: str,
    bucket: str,
    body: BinaryIO,
    options: Dict = {},
    client: boto3_session.client = None,
) -> str:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    client.put_object(Bucket=bucket, Key=key, Body=body, **options)
    return key
