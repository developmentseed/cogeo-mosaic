import functools
import json
from typing import BinaryIO, Dict, Optional, Tuple, Union

import mercantile
from boto3.session import Session as boto3_session

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import (
    _compress_gz_json,
    _decompress_gz,
    get_assets_from_json,
)
from cogeo_mosaic.model import MosaicJSON


class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    def __init__(
        self,
        bucket: str,
        key: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        client: Optional[boto3_session.client] = None,
    ):
        self.client = client or boto3_session().client("s3")
        self.key = key
        self.bucket = bucket

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read_mosaic(bucket, key)

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""

        return get_assets_from_json(self.mosaic_def.tiles, self.quadkey_zoom, x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""

        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return get_assets_from_json(
            self.mosaic_def.tiles, self.quadkey_zoom, tile.x, tile.y, tile.z
        )

    def upload(self):
        _aws_put_data(
            self.key,
            self.bucket,
            _compress_gz_json(dict(self.mosaic_def)),
            client=self.client,
        )

    def update(self):
        raise NotImplementedError

    @functools.lru_cache(maxsize=512)
    def read_mosaic(self, bucket: str, key: str) -> MosaicJSON:
        """Get Mosaic definition info."""

        body = _aws_get_data(key, bucket, client=self.client)

        if key.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))


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
