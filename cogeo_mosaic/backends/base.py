"""cogeo_mosaic.backend.base: base Backend class."""

import abc
from typing import Any, Dict, List, Optional, Sequence, Tuple

import attr
import mercantile
import numpy
from morecantile import TileMatrixSet
from rio_tiler.constants import MAX_THREADS, WEB_MERCATOR_TMS
from rio_tiler.errors import PointOutsideBounds
from rio_tiler.io import BaseReader, COGReader
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.tasks import create_tasks, filter_tasks

from cogeo_mosaic.backends.utils import get_hash
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union


@attr.s
class BaseBackend(BaseReader):
    """Base Class for cogeo-mosaic backend storage."""

    path: str = attr.ib()
    mosaic_def: MosaicJSON = attr.ib(default=None)
    reader: BaseReader = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    backend_options: Dict = attr.ib(factory=dict)
    minzoom: int = attr.ib(init=False)
    maxzoom: int = attr.ib(init=False)
    # TMS is outside the init because mosaicJSON and cogeo-mosaic only
    # works with WebMercator (mercantile) for now.
    tms: TileMatrixSet = attr.ib(init=False, default=WEB_MERCATOR_TMS)

    _backend_name: str
    _file_byte_size: Optional[int] = 0

    @mosaic_def.validator
    def _check_mosaic_def(self, attribute, value):
        if value is not None:
            self.mosaic_def = MosaicJSON(**dict(value))

    def __attrs_post_init__(self):
        """Post Init: if not passed in init, try to read from self.path."""
        self.mosaic_def = self.mosaic_def or self._read(**self.backend_options)
        self.minzoom = self.mosaic_def.minzoom
        self.maxzoom = self.mosaic_def.maxzoom

    def __enter__(self):
        """Support using with Context Managers."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Support using with Context Managers."""
        pass

    @property
    def bounds(self):
        """Mosaic Bounds."""
        return self.mosaic_def.bounds

    @property
    def center(self):
        """Mosaic center."""
        return self.mosaic_def.center

    def info(self):
        """Mosaic info."""
        return {
            "bounds": self.mosaic_def.bounds,
            "center": self.mosaic_def.center,
            "maxzoom": self.mosaic_def.maxzoom,
            "minzoom": self.mosaic_def.minzoom,
            "name": self.mosaic_def.name if self.mosaic_def.name else "mosaic",
            "quadkeys": list(self.mosaic_def.tiles),
        }

    def stats(self):
        """PlaceHolder for BaseReader.stats."""
        raise NotImplementedError

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
        self, x: int, y: int, z: int, reverse: bool = False, **kwargs: Any,
    ) -> Tuple[numpy.ndarray, numpy.ndarray]:
        """Get Tile from multiple observation."""
        assets = self.assets_for_tile(x, y, z)
        if not assets:
            raise NoAssetFoundError(f"No assets found for tile {z}-{x}-{y}")

        if reverse:
            assets = list(reversed(assets))

        def _reader(asset: str, x: int, y: int, z: int, **kwargs: Any):
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        return mosaic_reader(assets, _reader, x, y, z, **kwargs)

    def point(
        self,
        lon: float,
        lat: float,
        threads=MAX_THREADS,
        reverse: bool = False,
        **kwargs: Any,
    ) -> List[Dict]:
        """Get Point value from multiple observation."""
        assets = self.assets_for_point(lon, lat)
        if not assets:
            raise NoAssetFoundError(f"No assets found for point ({lon},{lat})")

        if reverse:
            assets = list(reversed(assets))

        def _reader(asset: str, lon: float, lat: float, **kwargs) -> Dict:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.point(lon, lat, **kwargs)

        tasks = create_tasks(_reader, assets, threads, lon, lat, **kwargs)
        return [
            {"asset": asset, "values": pt}
            for pt, asset in filter_tasks(
                tasks, allowed_exceptions=(PointOutsideBounds,)
            )
        ]

    def preview(self):
        """PlaceHolder for BaseReader.preview."""
        raise NotImplementedError

    def part(self):
        """PlaceHolder for BaseReader.part."""
        raise NotImplementedError

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
    def write(self, overwrite: bool = True):
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
            self.write(overwrite=True)

        return
