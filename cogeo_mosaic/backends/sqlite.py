"""cogeo-mosaic SQLite backend."""

import itertools
import json
import re
import sqlite3
import warnings
from pathlib import Path
from typing import Dict, List, Sequence
from urllib.parse import urlparse

import attr
import morecantile
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic import __version__ as cogeo_mosaic_version
from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import MosaicExistsError, MosaicNotFoundError
from cogeo_mosaic.logger import logger
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union

sqlite3.register_adapter(dict, json.dumps)
sqlite3.register_adapter(tuple, json.dumps)
sqlite3.register_adapter(list, json.dumps)
sqlite3.register_converter("JSON", json.loads)


MOSAIC_JSON_VERSION = 3


@attr.s
class SQLiteBackend(BaseBackend):
    """SQLite Backend Adapter."""

    db_path: str = attr.ib(init=False)
    mosaic_name: str = attr.ib(init=False)
    db: sqlite3.Connection = attr.ib(init=False)

    _backend_name = "SQLite"
    _metadata_table: str = "mosaicjson_metadata"

    def __attrs_post_init__(self):
        """Post Init: parse path connect to Table.

        A path looks like

        sqlite:///{db_path}:{mosaic_name}

        """
        if not re.match(
            r"^sqlite:///.+\:[a-zA-Z0-9\_\-\.]+$",
            self.input,
        ):
            raise ValueError(f"Invalid SQLite path: {self.input}")

        parsed = urlparse(self.input)
        uri_path = parsed.path[1:]  # remove `/` on the left

        self.mosaic_name = uri_path.split(":")[-1]
        assert (
            not self.mosaic_name == self._metadata_table
        ), f"'{self._metadata_table}' is a reserved table name."

        self.db_path = uri_path.replace(f":{self.mosaic_name}", "")

        # When mosaic_def is not passed, we have to make sure the db exists
        if not self.mosaic_def and not Path(self.db_path).exists():
            raise MosaicNotFoundError(
                f"SQLite database not found at path {self.db_path}."
            )

        self.db = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.db.row_factory = sqlite3.Row

        # Here we make sure the mosaicJSON.name is the same
        if self.mosaic_def and self.mosaic_def.name != self.mosaic_name:
            warnings.warn("Updating 'mosaic.name' to match table name.")
            self.mosaic_def.name = self.mosaic_name

        logger.debug(f"Using SQLite backend: {self.db_path}")
        super().__attrs_post_init__()

    def close(self):
        """Close SQLite connection."""
        self.db.close()

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        self.close()

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.input),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get Mosaic definition info."""
        meta = self._fetch_metadata()
        if not meta:
            raise MosaicNotFoundError(f"Mosaic not found in {self.input}")

        meta["tiles"] = {}
        return MosaicJSON(**meta)

    def write(self, overwrite: bool = False):
        """Write mosaicjson document to an SQLite database.

        Args:
            overwrite (bool): delete old mosaic items in the Table.

        Raises:
            MosaicExistsError: If mosaic already exists in the Table.

        """
        if self._mosaic_exists():
            if not overwrite:
                raise MosaicExistsError(
                    f"'{self.mosaic_name}' Table already exists in {self.db_path}, use `overwrite=True`."
                )
            self.delete()

        with self.db:
            logger.debug(
                f"Setting user_version to '{MOSAIC_JSON_VERSION}' in {self.db_path}."
            )
            self.db.execute(f"PRAGMA user_version = {MOSAIC_JSON_VERSION};")

            logger.debug(f"Creating '{self.mosaic_name}' Table in {self.db_path}.")
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
                        center JSON,
                        tilematrixset JSON,
                        asset_type TEXT,
                        asset_prefix TEXT,
                        data_type TEXT,
                        colormap JSON,
                        layers JSON
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
                        center,
                        tilematrixset,
                        asset_type,
                        asset_prefix,
                        data_type,
                        colormap,
                        layers
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
                        :center,
                        :tilematrixset,
                        :asset_type,
                        :asset_prefix,
                        :data_type,
                        :colormap,
                        :layers
                    );
                """,
                self.mosaic_def.model_dump(exclude={"tiles"}, mode="json"),
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
        logger.debug(f"Checking {self.db_path} version ...")
        with self.db:
            r = self.db.execute("PRAGMA user_version;").fetchone()
            assert (
                r[0] == MOSAIC_JSON_VERSION
            ), f"{self.db_path} is not compatible with this Backend version ({cogeo_mosaic_version})"

        logger.debug(f"Updating {self.mosaic_name}...")

        new_mosaic = MosaicJSON.from_features(
            features,
            self.mosaic_def.minzoom,
            self.mosaic_def.maxzoom,
            quadkey_zoom=self.quadkey_zoom,
            tilematrixset=self.mosaic_def.tilematrixset,
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
        self.bounds = bounds

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
                        center = :center,
                        tilematrixset = :tilematrixset,
                        asset_type = :asset_type,
                        asset_prefix = :asset_prefix,
                        data_type = :data_type,
                        colormap = :colormap,
                        layers = :layers
                    WHERE name=:name
                """,
                self.mosaic_def.model_dump(exclude={"tiles"}, mode="json"),
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

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, x, y, z: hashkey(self.input, x, y, z, self.mosaicid),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
        """Find assets."""
        mercator_tile = morecantile.Tile(x=x, y=y, z=z)
        quadkeys = self.find_quadkeys(mercator_tile, self.quadkey_zoom)
        assets = list(
            dict.fromkeys(
                itertools.chain.from_iterable([self._fetch(qk) for qk in quadkeys])
            )
        )
        if self.mosaic_def.asset_prefix:
            assets = [self.mosaic_def.asset_prefix + asset for asset in assets]

        return assets

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkey tiles."""
        with self.db:
            rows = self.db.execute(
                f'SELECT quadkey FROM "{self.mosaic_name}";',
            ).fetchall()
        return [r["quadkey"] for r in rows]

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
            f"Deleting all items for '{self.mosaic_name}' mosaic in {self.db_path}..."
        )
        with self.db:
            self.db.execute(
                f"DELETE FROM {self._metadata_table} WHERE name=?;", (self.mosaic_name,)
            )
            self.db.execute(f'DROP TABLE IF EXISTS "{self.mosaic_name}";')

    @classmethod
    def list_mosaics_in_db(
        cls,
        db_path: str,
    ) -> List[str]:
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
        parsed = urlparse(db_path)
        if parsed.scheme:
            db_path = parsed.path[1:]  # remove `/` on the left

        if not Path(db_path).exists():
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
