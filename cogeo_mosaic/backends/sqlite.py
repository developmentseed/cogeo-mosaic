"""cogeo-mosaic SQLite backend."""

import itertools
import json
from typing import Dict, List, Sequence
from urllib.parse import urlparse

import attr
import mercantile
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import (
    _HTTP_EXCEPTIONS,
    MosaicError,
    MosaicExistsError,
    MosaicNotFoundError,
)
from cogeo_mosaic.logger import logger
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union

try:
    import sqlite3
    from sqlite3 import Connection, OperationalError

    sqlite3.register_adapter(dict, json.dumps)
    sqlite3.register_converter("JSON", json.loads)
except ImportError:  # pragma: nocover
    sqlite3 = None  # type: ignore
    Connection = None  # type: ignore
    OperationalError = None  # type: ignore


@attr.s
class SQLiteBackend(BaseBackend):
    """SQLite Backend Adapter."""

    db_name: str = attr.ib(init=False)
    mosaic_name: str = attr.ib(init=False)

    db: Connection = attr.ib(init=False)

    _backend_name = "SQLite"
    _metadata_quadkey: str = "-1"

    def __attrs_post_init__(self):
        """Post Init: parse path connect to Table.

        A path looks like

        sqlite:///{db_name}:{mosaic_name}

        """
        assert sqlite3 is not None, "'sqlite3' must be installed to use SQLiteBackend"

        parsed = urlparse(self.path)
        mosaic_info = parsed.path.lstrip("/").split(":")
        self.db_name = mosaic_info[0]
        self.mosaic_name = mosaic_info[1]

        self.db = sqlite3.connect(self.db_name, detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row

        logger.debug(f"Using SQLite backend: {self.db_name}")
        super().__attrs_post_init__()

    def close(self):
        """Close SQLite connection."""
        self.db.close()

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        self.close()

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkey tiles."""
        with self.db:
            rows = self.db.execute(
                f"SELECT quadkey FROM {self.mosaic_name} WHERE quadkey != ?;",
                (self._metadata_quadkey,),
            ).fetchall()

        return [r["quadkey"] for r in rows]

    def write(self, overwrite: bool = False):
        """Write mosaicjson document to an SQLite database.

        Args:
            overwrite (bool): delete old mosaic items in the Table.

        Returns:
            dict: dictionary with metadata constructed from the sceneid.

        Raises:
            MosaicExistsError: If mosaic already exists in the Table.

        """
        if self._mosaic_exists():
            if not overwrite:
                raise MosaicExistsError(
                    f"'{self.mosaic_name}' Table already exists in {self.db_name}, use `overwrite=True`."
                )
            self.delete()

        logger.debug(f"Creating '{self.mosaic_name}' Table in {self.db_name}.")
        with self.db:
            self.db.execute(
                f"CREATE TABLE {self.mosaic_name} (quadkey TEXT NOT NULL, value JSON NOT NULL);",
            )

        logger.debug(f"Adding items in '{self.mosaic_name}' Table.")
        items = []
        items.append((self._metadata_quadkey, self.metadata.dict()))
        for qk, assets in self.mosaic_def.tiles.items():
            items.append((qk, {"assets": assets}))

        with self.db:
            self.db.executemany(
                f"INSERT INTO {self.mosaic_name} (quadkey, value) VALUES (?, ?);", items
            )

        return

    def _update_quadkey(self, quadkey: str, dataset: List[str]):
        """Update single quadkey in Table."""
        with self.db:
            self.db.execute(
                f"UPDATE {self.mosaic_name} SET value = ? WHERE quadkey=?;",
                ({"assets": dataset}, quadkey),
            )

    def _update_metadata(self):
        """Update bounds and center."""
        meta = self.metadata.dict()
        meta["mosaicId"] = self.mosaic_name
        with self.db:
            self.db.execute(
                f"UPDATE {self.mosaic_name} SET value = ? WHERE quadkey=?;",
                (meta, self._metadata_quadkey),
            )

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

        for quadkey, new_assets in new_mosaic.tiles.items():
            tile = mercantile.quadkey_to_tile(quadkey)
            assets = self.assets_for_tile(*tile)
            assets = [*new_assets, *assets] if add_first else [*assets, *new_assets]
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

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.path),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get Mosaic definition info."""
        meta = self._fetch(self._metadata_quadkey)
        if not meta:
            raise MosaicNotFoundError(f"Mosaic not found in {self.path}")

        meta["tiles"] = {}
        return MosaicJSON(**meta)

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, x, y, z: hashkey(self.path, x, y, z),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
        """Find assets."""
        mercator_tile = mercantile.Tile(x=x, y=y, z=z)
        quadkeys = find_quadkeys(mercator_tile, self.quadkey_zoom)
        return list(
            itertools.chain.from_iterable(
                [self._fetch(qk).get("assets", []) for qk in quadkeys]
            )
        )

    def _fetch(self, quadkey: str) -> Dict:
        try:
            with self.db:
                row = self.db.execute(
                    f"SELECT value FROM {self.mosaic_name} WHERE quadkey=?;", (quadkey,)
                ).fetchone()
                return row["value"] if row else {}
        except Exception as e:
            exc = _HTTP_EXCEPTIONS.get(404, MosaicError)
            raise exc(repr(e)) from e

    def _mosaic_exists(self) -> bool:
        """Check if the mosaic Table already exists."""
        with self.db:
            count = self.db.execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?;",
                (self.mosaic_name,),
            ).fetchone()
        return count[0] == 1

    def delete(self):
        """Delete a mosaic."""
        logger.debug(
            f"Deleting all items for '{self.mosaic_name}' mosaic in {self.db_name}..."
        )
        with self.db:
            self.db.execute(f"DROP TABLE IF EXISTS {self.mosaic_name};")
