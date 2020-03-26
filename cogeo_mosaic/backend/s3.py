import functools
from typing import BinaryIO, Dict

import mercantile
from boto3.session import Session as boto3_session

from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import get_assets_from_json
from cogeo_mosaic.utils import _decompress_gz


class S3Backend(BaseBackend):
    """S3 Backend Adapter"""

    def __enter__(self, bucket: str, key: str):
        self.mosaic_def = self.fetch_mosaic_definition(bucket, key)

    def tile(self, x: int, y: int, z: int, bucket: str, key: str):
        """Retrieve assets for tile."""

        return get_assets_from_json(self.mosaic_def, x, y, z)

    def point(self, lng: float, lat: float):
        """Retrieve assets for point."""

        min_zoom = self.mosaic_def["minzoom"]
        quadkey_zoom = self.mosaic_def.get("quadkey_zoom", min_zoom)  # 0.0.2
        tile = mercantile.tile(lng, lat, quadkey_zoom)
        return get_assets_from_json(self.mosaic_def, tile.x, tile.y, tile.z)

    @functools.lru_cache(maxsize=512)
    def fetch_mosaic_definition(self, bucket: str, key: str) -> Dict:
        """Get Mosaic definition info."""

        body = _aws_get_data(key, bucket)

        if key.endswith(".gz"):
            body = _decompress_gz(body)

        if isinstance(body, dict):
            return body
        else:
            return json.loads(body)


def _aws_get_data(key, bucket, client: boto3_session.client = None) -> BinaryIO:
    if not client:
        session = boto3_session()
        client = session.client("s3")
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
