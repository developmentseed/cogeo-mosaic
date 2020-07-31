"""cogeo_mosaic.backend.base: base Backend class."""

import abc
from concurrent import futures
from contextlib import AbstractContextManager
from typing import Any, Dict, List, Optional, Sequence, Tuple

import mercantile
import numpy
from rio_tiler.constants import MAX_THREADS
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.mosaic import _filter_tasks, mosaic_reader
from rio_tiler.mosaic.reader import TaskType

from cogeo_mosaic.backends.utils import get_hash
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union


class BaseBackend(AbstractContextManager):
    """Base Class for cogeo-mosaic backend storage."""

    path: str
    mosaic_def: MosaicJSON
    reader: BaseReader = COGReader
    _backend_name: str
    _file_byte_size: Optional[int] = 0

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        """Connect to backend"""

    def __enter__(self):
        """Support using with Context Managers"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers"""

    @property
    def metadata(self) -> Dict:
        """Retrieve Mosaic metadata

        Returns
        -------
        MosaicJSON as dict without `tiles` key.
        """
        return self.mosaic_def.dict(exclude={"tiles"}, exclude_none=True)

    @abc.abstractmethod
    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""

    def tile(
        self, x: int, y: int, z: int, **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Get Tile from multiple observation."""

        assets = self.assets_for_tile(x, y, z)
        if not assets:
            raise NoAssetFoundError(f"No assets found for tile {z}-{x}-{y}")

        def _reader(asset: str, x: int, y: int, z: int, **kwargs: Any):
            with self.reader(asset) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        return mosaic_reader(assets, _reader, x, y, z, **kwargs)

    def point(
        self, lon: float, lat: float, threads=MAX_THREADS, **kwargs: Any
    ) -> List[Dict]:
        """Get Point value from multiple observation."""
        assets = self.assets_for_point(lon, lat)
        if not assets:
            raise NoAssetFoundError(f"No assets found for point ({lon},{lat})")

        def _reader(asset: str, lon: float, lat: float, **kwargs) -> Dict:
            with self.reader(asset) as src_dst:
                return {"asset": asset, "value": src_dst.point(lon, lat, **kwargs)}

        tasks: TaskType

        if threads:
            with futures.ThreadPoolExecutor(max_workers=threads) as executor:
                tasks = [
                    executor.submit(_reader, asset, lon, lat, **kwargs)
                    for asset in assets
                ]
        else:
            tasks = (_reader(asset, lon, lat, **kwargs) for asset in assets)

        return list(_filter_tasks(tasks))

    @abc.abstractmethod
    def _read(self) -> MosaicJSON:
        """Fetch mosaic definition"""

    @property
    def mosaicid(self) -> str:
        """Return sha224 id of the mosaicjson document."""
        return get_hash(**self.mosaic_def.dict(exclude_none=True))

    @property
    def quadkey_zoom(self) -> int:
        """Return Quadkey zoom property."""
        return self.mosaic_def.quadkey_zoom or self.mosaic_def.minzoom

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkeys"""
        return list(self.mosaic_def.tiles.keys())

    @abc.abstractmethod
    def write(self):
        """Upload new MosaicJSON to backend."""

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

        for quadkey, new_assets in new_mosaic.tiles.items():
            tile = mercantile.quadkey_to_tile(quadkey)
            assets = self.assets_for_tile(*tile)
            assets = [*new_assets, *assets] if add_first else [*assets, *new_assets]

            # add custom sorting algorithm (e.g based on path name)
            self.mosaic_def.tiles[quadkey] = assets

        bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)

        self.mosaic_def._increase_version()
        self.mosaic_def.bounds = bounds
        self.mosaic_def.center = (
            (bounds[0] + bounds[2]) / 2,
            (bounds[1] + bounds[3]) / 2,
            self.mosaic_def.minzoom,
        )

        # We only write if path is set
        if self.path:
            self.write()

        return
