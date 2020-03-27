import functools
import itertools
import os
from typing import Dict, Tuple

import mercantile

from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import find_quadkeys


class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter"""

    def __init__(
        self, mosaicid: str, region: str = os.getenv("AWS_REGION", "us-east-1")
    ):
        self.client = boto3.resource("dynamodb", region_name=region)
        self.table = self.client.Table(mosaicid)
        self.mosaic_def = self.fetch_mosaic_definition()
        self.quadkey_zoom = self.mosaic_def.get(
            "quadkey_zoom", self.mosaic_def["minzoom"]
        )

    def tile(self, x: int, y: int, z: int, bucket: str, key: str) -> Tuple[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    @functools.lru_cache(maxsize=512)
    def fetch_mosaic_definition(self) -> Dict:
        """Get Mosaic definition info."""
        mosaic_def = fetch_dynamodb("-1")

        # Numeric values are loaded from DynamoDB as Decimal types
        # Convert maxzoom, minzoom, quadkey_zoom to float/int
        for key in ["minzoom", "maxzoom", "quadkey_zoom"]:
            if mosaic_def.get(key):
                mosaic_def[key] = int(mosaic_def[key])

        # Convert bounds, center to float/int
        for key in ["bounds", "center"]:
            if mosaic_def.get(key):
                mosaic_def[key] = list(map(float, mosaic_def[key]))

        return mosaic_def

    def get_assets(x: int, y: int, z: int) -> Tuple[str]:
        mercator_tile = mercantile.Tile(x=x, y=y, z=z)
        quadkeys = find_quadkeys(mercator_tile, self.quadkey_zoom)

        assets = list(
            itertools.chain.from_iterable(
                [fetch_dynamodb(qk).get("assets", []) for qk in quadkeys]
            )
        )

        # Find mosaics recursively?
        return assets

    def fetch_dynamodb(quadkey: str) -> Dict:
        return self.table.get_item(Key={"quadkey": quadkey}).get("Item", {})
