import functools
import itertools
import os
from typing import Dict, Tuple

import mercantile

from cogeo_mosaic.backend.base import BaseBackend


class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter"""

    def __init__(
        self, mosaicid: str, region: str = os.getenv("AWS_REGION", "us-east-1")
    ):
        self.client = boto3.resource("dynamodb", region_name=region)
        self.table = self.client.Table(mosaicid)
        self.mosaic_def = self.fetch_mosaic_definition()

    def metadata(self) -> Dict:
        return self.mosaic_def

    def tile(self, x: int, y: int, z: int, bucket: str, key: str) -> Tuple[str]:
        """Retrieve assets for tile."""

        return self.get_assets(x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""

        min_zoom = self.mosaic_def["minzoom"]
        quadkey_zoom = self.mosaic_def.get("quadkey_zoom", min_zoom)  # 0.0.2
        tile = mercantile.tile(lng, lat, quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    @functools.lru_cache(maxsize=512)
    def fetch_mosaic_definition(self) -> Dict:
        """Get Mosaic definition info."""
        # NOTE(kylebarron): may also want to convert Decimal to int/float here
        return fetch_dynamodb("-1")

    def get_assets(x: int, y: int, z: int) -> Tuple[str]:
        min_zoom = self.mosaic_def["minzoom"]
        quadkey_zoom = self.mosaic_def.get("quadkey_zoom", min_zoom)  # 0.0.2
        # quadkey_zoom is type Decimal when loaded from DynamoDB
        quadkey_zoom = int(quadkey_zoom)

        mercator_tile = mercantile.Tile(x=x, y=y, z=z)

        # get parent
        if mercator_tile.z > quadkey_zoom:
            depth = mercator_tile.z - quadkey_zoom
            for i in range(depth):
                mercator_tile = mercantile.parent(mercator_tile)
            quadkey = [mercantile.quadkey(*mercator_tile)]

        # get child
        elif mercator_tile.z < quadkey_zoom:
            depth = quadkey_zoom - mercator_tile.z
            mercator_tiles = [mercator_tile]
            for i in range(depth):
                mercator_tiles = sum(
                    [mercantile.children(t) for t in mercator_tiles], []
                )

            mercator_tiles = list(filter(lambda t: t.z == quadkey_zoom, mercator_tiles))
            quadkey = [mercantile.quadkey(*tile) for tile in mercator_tiles]
        else:
            quadkey = [mercantile.quadkey(*mercator_tile)]

        assets = list(
            itertools.chain.from_iterable(
                [fetch_dynamodb(table, qk).get("assets", []) for qk in quadkey]
            )
        )

        return assets

    def fetch_dynamodb(quadkey: str) -> Dict:
        return self.table.get_item(Key={"quadkey": quadkey}).get("Item", {})
