"""cogeo-mosaic AWS DynamoDB backend."""

import itertools
import json
import os
import sys
import warnings
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Union

import boto3
import click
import mercantile
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union


class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter."""

    _backend_name = "AWS DynamoDB"

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
        self.path = f"dynamodb://{region}/{table_name}"

        if mosaic_def is not None:
            self.mosaic_def = MosaicJSON(**dict(mosaic_def))
        else:
            self.mosaic_def = self._read()

    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkey tiles."""
        warnings.warn(
            "Performing full scan operation might be slow and expensive on large database."
        )
        resp = self.table.scan(ProjectionExpression="quadkey")  # TODO: Add pagination
        return [qk["quadkey"] for qk in resp["Items"] if qk["quadkey"] != "-1"]

    def write(self):
        """Write mosaicjson document to AWS DynamoDB."""
        self._create_table()
        items = self._create_items()
        self._write_items(items)

    def _update_quadkey(self, quadkey: str, dataset: List[str]):
        """Update quadkey list."""
        self.table.put_item(Item={"quadkey": quadkey, "assets": dataset})

    def _update_metadata(self):
        """Update bounds and center."""
        meta = json.loads(json.dumps(self.metadata), parse_float=Decimal)
        meta["quadkey"] = "-1"
        self.table.put_item(Item=meta)

    def update(
        self,
        features: Sequence[Dict],
        add_first: bool = True,
        quiet: bool = False,
        **kwargs,
    ):
        """Update existing MosaicJSON on backend."""
        new_mosaic = self.mosaic_def.from_features(
            features,
            self.mosaic_def.minzoom,
            self.mosaic_def.maxzoom,
            quadkey_zoom=self.quadkey_zoom,
            quiet=quiet,
            **kwargs,
        )

        fout = os.devnull if quiet else sys.stderr
        with click.progressbar(  # type: ignore
            new_mosaic.tiles.items(), file=fout, show_percent=True
        ) as items:
            for quadkey, new_assets in items:
                tile = mercantile.quadkey_to_tile(quadkey)
                assets = self.tile(*tile)
                assets = [*new_assets, *assets] if add_first else [*assets, *new_assets]

                # add custom sorting algorithm (e.g based on path name)
                self._update_quadkey(quadkey, assets)

        bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)

        self.mosaic_def._increase_version()
        self.mosaic_def.bounds = bounds
        self.mosaic_def.center = (
            (bounds[0] + bounds[2]) / 2,
            (bounds[1] + bounds[3]) / 2,
            self.mosaic_def.minzoom,
        )

        self._update_metadata()

        return

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
        except boto3.client("dynamodb").exceptions.ResourceInUseException:
            warnings.warn("Unable to create table, may already exist")
            return

    def _create_items(self) -> List[Dict]:
        items = []
        # Create one metadata item with quadkey=-1
        # Convert float to decimal
        # https://blog.ruanbekker.com/blog/2019/02/05/convert-float-to-decimal-data-types-for-boto3-dynamodb-using-python/
        meta = json.loads(json.dumps(self.metadata), parse_float=Decimal)

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
            ) as progitems:
                for item in progitems:
                    batch.put_item(item)

    @cached(
        TTLCache(maxsize=512, ttl=300), key=lambda self: hashkey(self.path),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
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

    @cached(
        TTLCache(maxsize=512, ttl=300),
        key=lambda self, x, y, z: hashkey(self.path, x, y, z),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
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
        try:
            return self.table.get_item(Key={"quadkey": quadkey}).get("Item", {})
        except ClientError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e
