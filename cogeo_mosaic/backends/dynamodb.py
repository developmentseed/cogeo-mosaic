"""cogeo-mosaic AWS DynamoDB backend."""

import itertools
import json
import os
import re
import sys
import warnings
from decimal import Decimal
from typing import Any, Dict, List, Sequence
from urllib.parse import urlparse

import attr
import boto3
import click
import mercantile
from botocore.exceptions import ClientError
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.cache import lru_cache
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError, MosaicExists
from cogeo_mosaic.logger import logger
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union


@attr.s
class DynamoDBBackend(BaseBackend):
    """DynamoDB Backend Adapter."""

    client: Any = attr.ib(default=None)
    region: str = attr.ib(default=os.getenv("AWS_REGION", "us-east-1"))
    table_name: str = attr.ib(init=False)
    mosaic_name: str = attr.ib(init=False)
    table: Any = attr.ib(init=False)

    _backend_name = "AWS DynamoDB"

    def __attrs_post_init__(self):
        """Post Init: parse path, create client and connect to Table.

        A path looks like

        dynamodb://{region}/{table_name}:{mosaic_name}
        dynamodb:///{table_name}:{mosaic_name}

        """
        logger.debug(f"Using DynamoDB backend: {self.path}")

        if not re.match(
            r"dynamodb://([a-z]{2}\-[a-z]+\-[0-9])?\/[a-zA-Z0-9\_\-\.]+\:[a-zA-Z0-9\_\-\.]+$",
            self.path,
        ):
            raise ValueError(f"Invalid DynamoDB path: {self.path}")

        parsed = urlparse(self.path)

        mosaic_info = parsed.path.lstrip("/").split(":")
        self.table_name = mosaic_info[0]
        self.mosaic_name = mosaic_info[1]

        logger.debug(f"Table: {self.table_name}")
        logger.debug(f"Mosaic: {self.mosaic_name}")

        self.region = parsed.netloc or self.region
        self.client = self.client or boto3.resource("dynamodb", region_name=self.region)
        self.table = self.client.Table(self.table_name)
        super().__attrs_post_init__()

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = mercantile.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    def info(self, quadkeys: bool = False):
        """Mosaic info."""
        return {
            "bounds": self.mosaic_def.bounds,
            "center": self.mosaic_def.center,
            "maxzoom": self.mosaic_def.maxzoom,
            "minzoom": self.mosaic_def.minzoom,
            "name": self.mosaic_def.name if self.mosaic_def.name else "mosaic",
            "quadkeys": [] if not quadkeys else self._quadkeys,
        }

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkey tiles."""
        resp = self.table.query(
            KeyConditionExpression="#mosaicId = :mosaicId",
            # allows you to use dyanmodb reserved keywords as field names
            ExpressionAttributeNames={"#mosaicId": "mosaicId", "#quadKey": "quadKey"},
            ExpressionAttributeValues={":mosaicId": {"S": self.mosaic_name}},
            ProjectionExpression="#quadKey",
        )
        return [qk["quadkey"] for qk in resp["Items"] if qk["quadkey"] != "-1"]

    def write(self, overwrite: bool = False, **kwargs: Any):
        """Write mosaicjson document to AWS DynamoDB."""
        if not self._table_exists():
            self._create_table(**kwargs)

        if self._mosaic_exists():
            if not overwrite:
                raise MosaicExists(
                    f"Mosaic already exists in {self.table_name}, use `overwrite=True`."
                )
            self.clean()

        items = self._create_items()
        self._write_items(items)

    def _update_quadkey(self, quadkey: str, dataset: List[str]):
        """Update single quadkey in DynamoDB."""
        self.table.put_item(
            Item={"mosaicId": self.mosaic_name, "quadkey": quadkey, "assets": dataset}
        )

    def _update_metadata(self):
        """Update bounds and center."""
        meta = json.loads(json.dumps(self.metadata), parse_float=Decimal)
        meta["quadkey"] = "-1"
        meta["mosaicId"] = self.mosaic_name
        self.table.put_item(Item=meta)

    def update(
        self,
        features: Sequence[Dict],
        add_first: bool = True,
        quiet: bool = False,
        **kwargs,
    ):
        """Update existing MosaicJSON on backend."""
        logger.debug(f"Updating {self.mosaic_name}...")

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
                assets = self.assets_for_tile(*tile)
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

    def _create_table(self, billing_mode: str = "PAY_PER_REQUEST", **kwargs: Any):
        """Create DynamoDB Table."""
        logger.debug(f"Creating {self.table_name} Table.")

        # Define schema for primary key
        # Non-keys don't need a schema
        attr_defs = [
            {"AttributeName": "mosaicId", "AttributeType": "S"},
            {"AttributeName": "quadkey", "AttributeType": "S"},
        ]
        key_schema = [
            {"AttributeName": "mosaicId", "KeyType": "RANGE"},
            {"AttributeName": "quadkey", "KeyType": "HASH"},
        ]

        # Note: errors if table already exists
        try:
            self.client.create_table(
                AttributeDefinitions=attr_defs,
                TableName=self.table.table_name,
                KeySchema=key_schema,
                BillingMode=billing_mode,
                **kwargs,
            )

            # If outside try/except block, could wait forever if unable to
            # create table
            self.table.wait_until_exists()
        except self.table.meta.client.exceptions.ResourceNotFoundException:
            warnings.warn("Unable to create table.")
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
            item = {"mosaicId": self.mosaic_name, "quadkey": quadkey, "assets": assets}
            items.append(item)

        return items

    def _write_items(self, items: List[Dict]):
        with self.table.batch_writer() as batch:
            with click.progressbar(
                items, length=len(items), show_percent=True
            ) as progitems:
                for item in progitems:
                    batch.put_item(item)

    @lru_cache(key=lambda self: hashkey(self.path),)
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get Mosaic definition info."""
        meta = self._fetch_dynamodb("-1")

        # Numeric values are loaded from DynamoDB as Decimal types
        # Convert maxzoom, minzoom, quadkey_zoom to int
        for key in ["minzoom", "maxzoom", "quadkey_zoom"]:
            if meta.get(key):
                meta[key] = int(meta[key])

        # Convert bounds, center to float
        for key in ["bounds", "center"]:
            if meta.get(key):
                meta[key] = list(map(float, meta[key]))

        # Create pydantic class
        # For now, a tiles key must exist
        meta["tiles"] = {}
        return MosaicJSON(**meta)

    @lru_cache(key=lambda self, x, y, z: hashkey(self.path, x, y, z),)
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
            return self.table.get_item(
                Key={"mosaicId": self.mosaic_name, "quadkey": quadkey}
            ).get("Item", {})
        except ClientError as e:
            status_code = e.response["ResponseMetadata"]["HTTPStatusCode"]
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response["Error"]["Message"]) from e

    def _table_exists(self) -> bool:
        """Check if the Table already exists."""
        try:
            _ = self.table.table_status
            return True
        except self.table.meta.client.exceptions.ResourceNotFoundException:
            return False

    def _mosaic_exists(self) -> bool:
        """Check if the mosaic already exists in the Table."""
        item = self.table.get_item(
            Key={"mosaicId": self.mosaic_name, "quadkey": "-1"}
        ).get("Item", {})

        return True if item else False

    def clean(self):
        """clean MosaicID from dynamoDB Table."""
        logger.debug(f"Deleting items for mosaic {self.mosaic_name}...")

        # get items
        resp = self.table.query(
            KeyConditionExpression="#mosaicId = :mosaicId",
            ExpressionAttributeNames={"#mosaicId": "mosaicId", "#quadKey": "quadKey"},
            ExpressionAttributeValues={":mosaicId": {"S": self.mosaic_name}},
            ProjectionExpression="#quadKey",
        )

        # delete items
        for i in resp["Items"]:
            self.client.batch_write_item(
                RequestItems={
                    self.table_name: [
                        {
                            "DeleteRequest": {
                                "Key": {
                                    "mosaicId": {"S": i["mosaicId"]},
                                    "quadkey": {"S": i["quadkey"]},
                                }
                            }
                        }
                    ]
                }
            )
