"""cogeo-mosaic AWS DynamoDB backend."""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import functools
import itertools
import json
import os
import warnings
from decimal import Decimal

import boto3
import click
import mercantile

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.model import MosaicJSON


class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter."""

    def __init__(
        self,
        table_name: str,
        mosaic_def: Optional[Union[MosaicJSON, Dict]] = None,
        region: str = os.getenv("AWS_REGION", "us-east-1"),
        client: Optional[Any] = None,
    ):
        """Initialize DynamoDBBackend."""
        self.client = client or boto3.resource("dynamodb", region_name=region)
        self.table = self.client.Table(table_name)

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self.read()

    def tile(self, x: int, y: int, z: int) -> Tuple[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def point(self, lng: float, lat: float) -> Tuple[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    def write(self):
        """Write mosaicjson document to AWS DynamoDB."""
        self._create_table()
        items = self._create_items()
        self._write_items(items)

    def update(self):
        """Update the mosaicjson document."""
        raise NotImplementedError

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

            # If outside try/except block, could wait forever if unable to
            # create table
            self.table.wait_until_exists()
        except self.client.exceptions.ResourceInUseException:
            warnings.warn("Unable to create table, may already exist")
            return

    def _create_items(self) -> List[Dict]:
        items = []
        # Create one metadata item with quadkey=-1
        # Convert float to decimal
        # https://blog.ruanbekker.com/blog/2019/02/05/convert-float-to-decimal-data-types-for-boto3-dynamodb-using-python/
        meta = json.loads(json.dumps(self.metadata, parse_float=Decimal))

        # NOTE: quadkey is a string type
        meta["quadkey"] = "-1"
        items.append(meta)

        for quadkey, assets in self.mosaic_def.tiles.items():
            item = {"quadkey": quadkey, "assets": assets}
            items.append(item)

        return items

    def _write_items(self, items: List[Dict]):
        with self.table.batch_writer() as batch:
            with click.progressbar(
                items, length=len(items), show_percent=True
            ) as items:
                for item in items:
                    batch.put_item(item)

    @functools.lru_cache(maxsize=512)
    def read(self) -> MosaicJSON:
        """Get Mosaic definition info."""
        meta = self._fetch_dynamodb("-1")

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

    @functools.lru_cache(maxsize=512)
    def get_assets(self, x: int, y: int, z: int) -> Sequence[str]:
        """Find assets."""
        mercator_tile = mercantile.Tile(x=x, y=y, z=z)
        quadkeys = find_quadkeys(mercator_tile, self.quadkey_zoom)

        assets = list(
            itertools.chain.from_iterable(
                [self._fetch_dynamodb(qk).get("assets", []) for qk in quadkeys]
            )
        )

        # Find mosaics recursively?
        return assets

    def _fetch_dynamodb(self, quadkey: str) -> Dict:
        return self.table.get_item(Key={"quadkey": quadkey}).get("Item", {})
