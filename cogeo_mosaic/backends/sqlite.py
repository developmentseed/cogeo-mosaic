"""cogeo-mosaic SQLite backend."""

import itertools
import json
import os
import sqlite3
import warnings
from typing import Dict, List, Sequence, Type

import attr
import mercantile
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from morecantile import TileMatrixSet
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.io import BaseReader, COGReader

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import MosaicExistsError, MosaicNotFoundError
from cogeo_mosaic.logger import logger
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union

sqlite3.register_adapter(dict, json.dumps)
sqlite3.register_adapter(tuple, json.dumps)
sqlite3.register_adapter(list, json.dumps)
sqlite3.register_converter("JSON", json.loads)


@attr.s
class SQLiteBackend(BaseBackend):
    """SQLite Backend Adapter."""

    path: str = attr.ib()
    mosaic_name: str = attr.ib()

    mosaic_def: MosaicJSON = attr.ib(default=None)
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    backend_options: Dict = attr.ib(factory=dict)

    tms: TileMatrixSet = attr.ib(init=False, default=WEB_MERCATOR_TMS)

    db: sqlite3.Connection = attr.ib(init=False)

    _backend_name = "SQLite"
    _metadata_table: str = "mosaicjson_metadata"

    @mosaic_name.validator
    def _check_mosaic_name(self, attribute, value):
        assert (
            not value == self._metadata_table
        ), f"'{self._metadata_table}' is a reserved table name."

    @mosaic_def.validator
    def _check_mosaic_def(self, attribute, value):
        if value is not None:
            self.mosaic_def = MosaicJSON(**dict(value))

    def __attrs_post_init__(self):
        """Post Init: parse path connect to Table."""
        # When mosaic_def is not passed, we have to make sure the db exists
        if not self.mosaic_def and not os.path.exists(self.path):
            raise MosaicNotFoundError(f"SQLite database not found at path {self.path}.")

        self.db = sqlite3.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row

        # Here we make sure the mosaicJSON.name is the same
        if self.mosaic_def and self.mosaic_def.name != self.mosaic_name:
            warnings.warn("Updating 'mosaic.name' to match table name.")
            self.mosaic_def.name = self.mosaic_name

        logger.debug(f"Using SQLite backend: {self.path}")
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
                f'SELECT quadkey FROM "{self.mosaic_name}";',
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
                    f"'{self.mosaic_name}' Table already exists in {self.path}, use `overwrite=True`."
                )
            self.delete()

        logger.debug(f"Creating '{self.mosaic_name}' Table in {self.path}.")
        with self.db:
            self.db.execute(
                f"""
                    CREATE TABLE IF NOT EXISTS {self._metadata_table}
                    (
                        mosaicjson TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        version TEXT NOT NULL,
                        attribution TEXT,
                        minzoom INTEGER NOT NULL,
                        maxzoom INTEGER NOT NULL,
                        quadkey_zoom INTEGER,
                        bounds JSON NOT NULL,
                        center JSON
                    );
                """
            )
            self.db.execute(
                f"""
                    CREATE TABLE "{self.mosaic_name}"
                    (
                        quadkey TEXT NOT NULL,
                        assets JSON NOT NULL
                    );
                """
            )

        logger.debug(f"Adding items in '{self.mosaic_name}' Table.")
        with self.db:
            self.db.execute(
                f"""
                    INSERT INTO {self._metadata_table}
                    (
                        mosaicjson,
                        name,
                        description,
                        version,
                        attribution,
                        minzoom,
                        maxzoom,
                        quadkey_zoom,
                        bounds,
                        center
                    )
                    VALUES
                    (
                        :mosaicjson,
                        :name,
                        :description,
                        :version,
                        :attribution,
                        :minzoom,
                        :maxzoom,
                        :quadkey_zoom,
                        :bounds,
                        :center
                    );
                """,
                self.metadata.dict(),
            )

            self.db.executemany(
                f'INSERT INTO "{self.mosaic_name}" (quadkey, assets) VALUES (?, ?);',
                self.mosaic_def.tiles.items(),
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

        new_mosaic = MosaicJSON.from_features(
            features,
            self.mosaic_def.minzoom,
            self.mosaic_def.maxzoom,
            quadkey_zoom=self.quadkey_zoom,
            quiet=quiet,
            **kwargs,
        )

        bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)

        self.mosaic_def._increase_version()
        self.mosaic_def.bounds = bounds
        self.mosaic_def.center = (
            (bounds[0] + bounds[2]) / 2,
            (bounds[1] + bounds[3]) / 2,
            self.mosaic_def.minzoom,
        )

        with self.db:
            self.db.execute(
                f"""
                    UPDATE {self._metadata_table}
                    SET mosaicjson = :mosaicjson,
                        name = :name,
                        description = :description,
                        version = :version,
                        attribution = :attribution,
                        minzoom = :minzoom,
                        maxzoom = :maxzoom,
                        quadkey_zoom = :quadkey_zoom,
                        bounds = :bounds,
                        center = :center
                    WHERE name=:name
                """,
                self.mosaic_def.dict(),
            )

            if add_first:
                self.db.executemany(
                    f"""
                        UPDATE "{self.mosaic_name}"
                        SET assets = (
                            SELECT json_group_array(value)
                            FROM (
                                SELECT value FROM json_each(?)
                                UNION ALL
                                SELECT value FROM json_each(assets)
                            )
                        )
                        WHERE quadkey=?;
                    """,
                    [(assets, qk) for qk, assets in new_mosaic.tiles.items()],
                )

            else:
                self.db.executemany(
                    f"""
                        UPDATE "{self.mosaic_name}"
                        SET assets = (
                            SELECT json_group_array(value)
                            FROM (
                                SELECT value FROM json_each(assets)
                                UNION ALL
                                SELECT value FROM json_each(?)
                            )
                        )
                        WHERE quadkey=?;
                    """,
                    [(assets, qk) for qk, assets in new_mosaic.tiles.items()],
                )

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.path, self.mosaic_name),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get Mosaic definition info."""
        meta = self._fetch_metadata()
        if not meta:
            raise MosaicNotFoundError(f"Mosaic not found in {self.path}")

        meta["tiles"] = {}
        return MosaicJSON(**meta)

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, x, y, z: hashkey(self.path, x, y, z, self.mosaicid),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
        """Find assets."""
        mercator_tile = mercantile.Tile(x=x, y=y, z=z)
        quadkeys = find_quadkeys(mercator_tile, self.quadkey_zoom)
        return list(itertools.chain.from_iterable([self._fetch(qk) for qk in quadkeys]))

    def _fetch_metadata(self) -> Dict:
        with self.db:
            row = self.db.execute(
                f"SELECT * FROM {self._metadata_table} WHERE name=?;",
                (self.mosaic_name,),
            ).fetchone()
            return dict(row) if row else {}

    def _fetch(self, quadkey: str) -> List:
        with self.db:
            row = self.db.execute(
                f'SELECT assets FROM "{self.mosaic_name}" WHERE quadkey=?;', (quadkey,)
            ).fetchone()
            return row["assets"] if row else []

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
            f"Deleting all items for '{self.mosaic_name}' mosaic in {self.path}..."
        )
        with self.db:
            self.db.execute(
                f"DELETE FROM {self._metadata_table} WHERE name=?;", (self.mosaic_name,)
            )
            self.db.execute(f'DROP TABLE IF EXISTS "{self.mosaic_name}";')

    @classmethod
    def list_mosaics_in_db(cls, db_path: str,) -> List[str]:
        """List Mosaic tables in SQLite database.

        Args:
            db_path (str): SQLite file.

        Returns:
            list: list of mosaic names in database.

        Raises:
            ValueError: if file does NOT exists.

        Examples:
            >>> SQLiteBackend.list_mosaics_in_db("mosaics.db")
            ["test"]

        """
        if not os.path.exists(db_path):
            raise ValueError(f"SQLite database not found at path '{db_path}'.")

        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        with db:
            rows = db.execute(f"SELECT name FROM {cls._metadata_table};").fetchall()
            rows_table = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table';",
            ).fetchall()
        db.close()

        names_in_metadata = [r["name"] for r in rows]
        all_tables = [r["name"] for r in rows_table]

        for name in names_in_metadata:
            if name not in all_tables:
                warnings.warn(f"'{name}' found in metadata, but table does not exists.")

        return [r for r in names_in_metadata if r in all_tables]
