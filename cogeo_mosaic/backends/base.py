"""cogeo_mosaic.backend.base: base Backend class."""

import abc
import itertools
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import attr
import morecantile
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import PointOutsideBounds
from rio_tiler.io import BaseReader, COGReader, MultiBandReader, MultiBaseReader
from rio_tiler.models import ImageData
from rio_tiler.mosaic import mosaic_reader
from rio_tiler.tasks import multi_values

from cogeo_mosaic.backends.utils import get_hash
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.models import Info
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import bbox_union


def _convert_to_mosaicjson(value: Union[Dict, MosaicJSON]):
    if value is not None:
        return MosaicJSON(**dict(value))


@attr.s
class BaseBackend(BaseReader):
    """Base Class for cogeo-mosaic backend storage.

    Attributes:
        input (str): mosaic path.
        mosaic_def (MosaicJSON, optional): mosaicJSON document.
        reader (rio_tiler.io.BaseReader): Dataset reader. Defaults to `rio_tiler.io.COGReader`.
        reader_options (dict): Options to forward to the reader config.
        geographic_crs (rasterio.crs.CRS, optional): CRS to use as geographic coordinate system. Defaults to WGS84.
        tms (morecantile.TileMatrixSet, optional): TileMatrixSet grid definition. **READ ONLY attribute**. Defaults to `WebMercatorQuad`.
        bbox (tuple): mosaic bounds (left, bottom, right, top). **READ ONLY attribute**. Defaults to `(-180, -90, 180, 90)`.
        minzoom (int): mosaic Min zoom level. **READ ONLY attribute**. Defaults to `0`.
        maxzoom (int): mosaic Max zoom level. **READ ONLY attribute**. Defaults to `30`

    """

    input: str = attr.ib()
    mosaic_def: MosaicJSON = attr.ib(default=None, converter=_convert_to_mosaicjson)

    reader: Union[
        Type[BaseReader],
        Type[MultiBaseReader],
        Type[MultiBandReader],
    ] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    # TMS is outside the init because mosaicJSON and cogeo-mosaic only
    # works with WebMercator for now.
    tms: TileMatrixSet = attr.ib(init=False, default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(init=False)
    maxzoom: int = attr.ib(init=False)

    # default values for bounds
    bounds: Tuple[float, float, float, float] = attr.ib(
        init=False, default=(-180, -90, 180, 90)
    )
    crs: CRS = attr.ib(init=False, default=WGS84_CRS)

    _backend_name: str
    _file_byte_size: Optional[int] = 0

    def __attrs_post_init__(self):
        """Post Init: if not passed in init, try to read from self.input."""
        self.mosaic_def = self.mosaic_def or self._read()
        self.minzoom = self.mosaic_def.minzoom
        self.maxzoom = self.mosaic_def.maxzoom
        self.bounds = self.mosaic_def.bounds

    @abc.abstractmethod
    def _read(self) -> MosaicJSON:
        """Fetch mosaic definition"""

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
        new_mosaic = MosaicJSON.from_features(
            features,
            self.mosaic_def.minzoom,
            self.mosaic_def.maxzoom,
            quadkey_zoom=self.quadkey_zoom,
            quiet=quiet,
            **kwargs,
        )

        for quadkey, new_assets in new_mosaic.tiles.items():
            tile = self.tms.quadkey_to_tile(quadkey)
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
        self.bounds = bounds
        self.write(overwrite=True)

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        return self.get_assets(x, y, z)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""
        tile = self.tms.tile(lng, lat, self.quadkey_zoom)
        return self.get_assets(tile.x, tile.y, tile.z)

    def assets_for_bbox(
        self, xmin: float, ymin: float, xmax: float, ymax: float
    ) -> List[str]:
        """Retrieve assets for bbox."""
        tl_tile = self.tms.tile(xmin, ymax, self.quadkey_zoom)
        br_tile = self.tms.tile(xmax, ymin, self.quadkey_zoom)

        tiles = [
            (x, y, self.quadkey_zoom)
            for x in range(tl_tile.x, br_tile.x + 1)
            for y in range(tl_tile.y, br_tile.y + 1)
        ]

        return list(
            dict.fromkeys(
                itertools.chain.from_iterable([self.assets_for_tile(*t) for t in tiles])
            )
        )

    @cached(
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, x, y, z: hashkey(self.input, x, y, z, self.mosaicid),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
        """Find assets."""
        mercator_tile = morecantile.Tile(x=x, y=y, z=z)
        quadkeys = self.find_quadkeys(mercator_tile, self.quadkey_zoom)
        return list(
            dict.fromkeys(
                itertools.chain.from_iterable(
                    [self.mosaic_def.tiles.get(qk, []) for qk in quadkeys]
                )
            )
        )

    def find_quadkeys(
        self, mercator_tile: morecantile.Tile, quadkey_zoom: int
    ) -> List[str]:
        """
        Find quadkeys at desired zoom for tile

        Attributes
        ----------
        mercator_tile: morecantile.Tile
            Input tile to use when searching for quadkeys
        quadkey_zoom: int
            Zoom level

        Returns
        -------
        list
            List[str] of quadkeys

        """
        # get parent
        if mercator_tile.z > quadkey_zoom:
            depth = mercator_tile.z - quadkey_zoom
            for _ in range(depth):
                mercator_tile = self.tms.parent(mercator_tile)[0]
            return [self.tms.quadkey(*mercator_tile)]

        # get child
        elif mercator_tile.z < quadkey_zoom:
            depth = quadkey_zoom - mercator_tile.z
            mercator_tiles = [mercator_tile]
            for _ in range(depth):
                mercator_tiles = sum([self.tms.children(t) for t in mercator_tiles], [])

            mercator_tiles = list(filter(lambda t: t.z == quadkey_zoom, mercator_tiles))
            return [self.tms.quadkey(*tile) for tile in mercator_tiles]
        else:
            return [self.tms.quadkey(*mercator_tile)]

    def tile(  # type: ignore
        self,
        x: int,
        y: int,
        z: int,
        reverse: bool = False,
        **kwargs: Any,
    ) -> Tuple[ImageData, List[str]]:
        """Get Tile from multiple observation."""
        mosaic_assets = self.assets_for_tile(x, y, z)
        if not mosaic_assets:
            raise NoAssetFoundError(f"No assets found for tile {z}-{x}-{y}")

        if reverse:
            mosaic_assets = list(reversed(mosaic_assets))

        def _reader(asset: str, x: int, y: int, z: int, **kwargs: Any) -> ImageData:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        return mosaic_reader(mosaic_assets, _reader, x, y, z, **kwargs)

    def point(
        self,
        lon: float,
        lat: float,
        reverse: bool = False,
        **kwargs: Any,
    ) -> List:
        """Get Point value from multiple observation."""
        mosaic_assets = self.assets_for_point(lon, lat)
        if not mosaic_assets:
            raise NoAssetFoundError(f"No assets found for point ({lon},{lat})")

        if reverse:
            mosaic_assets = list(reversed(mosaic_assets))

        def _reader(asset: str, lon: float, lat: float, **kwargs) -> Dict:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.point(lon, lat, **kwargs)

        if "allowed_exceptions" not in kwargs:
            kwargs.update({"allowed_exceptions": (PointOutsideBounds,)})

        return list(multi_values(mosaic_assets, _reader, lon, lat, **kwargs).items())

    def info(self, quadkeys: bool = False) -> Info:  # type: ignore
        """Mosaic info."""
        return Info(
            bounds=self.mosaic_def.bounds,
            center=self.mosaic_def.center,
            maxzoom=self.mosaic_def.maxzoom,
            minzoom=self.mosaic_def.minzoom,
            name=self.mosaic_def.name if self.mosaic_def.name else "mosaic",
            quadkeys=[] if not quadkeys else self._quadkeys,
        )

    @property
    def center(self):
        """Return center from the mosaic definition."""
        return self.mosaic_def.center

    @property
    def mosaicid(self) -> str:
        """Return sha224 id of the mosaicjson document."""
        return get_hash(**self.mosaic_def.dict(exclude_none=True))

    @property
    def _quadkeys(self) -> List[str]:
        """Return the list of quadkey tiles."""
        return list(self.mosaic_def.tiles)

    @property
    def quadkey_zoom(self) -> int:
        """Return Quadkey zoom property."""
        return self.mosaic_def.quadkey_zoom or self.mosaic_def.minzoom

    ############################################################################
    # Not Implemented methods
    # BaseReader required those method to be implemented
    def statistics(self):
        """PlaceHolder for BaseReader.statistics."""
        raise NotImplementedError

    def preview(self):
        """PlaceHolder for BaseReader.preview."""
        raise NotImplementedError

    def part(self):
        """PlaceHolder for BaseReader.part."""
        raise NotImplementedError

    def feature(self):
        """PlaceHolder for BaseReader.feature."""
        raise NotImplementedError
