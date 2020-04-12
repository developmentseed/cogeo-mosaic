import functools
import itertools
import json
import logging
import os
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

import boto3
import mercantile

from cogeo_mosaic.backend.base import BaseBackend
from cogeo_mosaic.backend.utils import find_quadkeys
from cogeo_mosaic.model import MosaicJSON

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter"""

    def __init__(
        self,
        table_name: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        region: str = os.getenv("AWS_REGION", "us-east-1"),
        client: Optional[Any] = None,
    ):
        self.client = client or boto3.resource("dynamodb", region_name=region)
        self.table = self.client.Table(table_name)

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read_mosaic()

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    def upload(self):
        self._create_table()
        items = self._create_items()
        self._upload_items(items)

    def _create_table(self, billing_mode: str = "PAY_PER_REQUEST"):
        # Define schema for primary key
        # Non-keys don't need a schema
        attr_defs = [{"AttributeName": "quadkey", "AttributeType": "S"}]
        key_schema = [{"AttributeName": "quadkey", "KeyType": "HASH"}]

        # Note: errors if table already exists
        try:
            self.client.create_table(
                AttributeDefinitions=attr_defs,
                TableName=self.table.table_name,
                KeySchema=key_schema,
                BillingMode=billing_mode,
            )
            logger.info("creating table")

            # If outside try/except block, could wait forever if unable to
            # create table
            self.table.wait_until_exists()
        except boto3.client("dynamodb").exceptions.ResourceInUseException:
            logger.warn("unable to create table, may already exist")

    def _create_items(self) -> List[Dict]:
        items = []
        # Create one metadata item with quadkey=-1
        # Convert float to decimal
        # https://blog.ruanbekker.com/blog/2019/02/05/convert-float-to-decimal-data-types-for-boto3-dynamodb-using-python/
        meta = json.loads(json.dumps(self.metadata()), parse_float=Decimal)

        # NOTE: quadkey is a string type
        meta["quadkey"] = "-1"
        items.append(meta)

        for quadkey, assets in self.mosaic_def.tiles.items():
            item = {"quadkey": quadkey, "assets": assets}
            items.append(item)

        return items

    def _upload_items(self, items: List[Dict]):
        with self.table.batch_writer() as batch:
            logger.info(f"Uploading items to table {self.table.table_name}")
            counter = 0
            for item in items:
                if counter % 1000 == 0:
                    logger.info(f"Uploading #{counter}")

                batch.put_item(item)
                counter += 1

    @functools.lru_cache(maxsize=512)
    def read_mosaic(self) -> MosaicJSON:
        """Get Mosaic definition info."""
        meta = self.fetch_dynamodb("-1")

        # Numeric values are loaded from DynamoDB as Decimal types
        # Convert maxzoom, minzoom, quadkey_zoom to float/int
        for key in ["minzoom", "maxzoom", "quadkey_zoom"]:
            if meta.get(key):
                meta[key] = int(meta[key])

        # Convert bounds, center to float/int
        for key in ["bounds", "center"]:
            if meta.get(key):
                meta[key] = list(map(float, meta[key]))

        # Create pydantic class
        # For now, a tiles key must exist
        meta["tiles"] = {}
        return MosaicJSON(**meta)

    def get_assets(self, x: int, y: int, z: int) -> Tuple[str]:
        mercator_tile = mercantile.Tile(x=x, y=y, z=z)
        quadkeys = find_quadkeys(mercator_tile, self.quadkey_zoom)

        assets = list(
            itertools.chain.from_iterable(
                [self.fetch_dynamodb(qk).get("assets", []) for qk in quadkeys]
            )
        )

        # Find mosaics recursively?
        return assets

    def fetch_dynamodb(self, quadkey: str) -> Dict:
        return self.table.get_item(Key={"quadkey": quadkey}).get("Item", {})
