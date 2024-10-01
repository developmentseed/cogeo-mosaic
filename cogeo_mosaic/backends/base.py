"""cogeo_mosaic.backend.base: base Backend class."""

import abc
import itertools
import warnings
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

import attr
from cachetools import TTLCache, cached
from cachetools.keys import hashkey
from morecantile import Tile, TileMatrixSet
from rasterio.crs import CRS
from rasterio.warp import transform, transform_bounds
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.errors import PointOutsideBounds
from rio_tiler.io import BaseReader, MultiBandReader, MultiBaseReader, Reader
from rio_tiler.models import ImageData, PointData
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
        tms (morecantile.TileMatrixSet, optional): TileMatrixSet grid definition. Defaults to `WebMercatorQuad`.
        minzoom (int): mosaic Min zoom level. Defaults to tms or mosaic minzoom.
        maxzoom (int): mosaic Max zoom level. Defaults to tms or mosaic maxzoom.
        reader (rio_tiler.io.BaseReader): Dataset reader. Defaults to `rio_tiler.io.Reader`.
        reader_options (dict): Options to forward to the reader config.
        bounds (tuple): mosaic bounds (left, bottom, right, top). **READ ONLY attribute**. Defaults to `(-180, -90, 180, 90)`.
        crs (rasterio.crs.CRS): mosaic crs in which its bounds is defined. **READ ONLY attribute**. Defaults to WGS84.
        geographic_crs (rasterio.crs.CRS, optional): CRS to use as geographic coordinate system. **READ ONLY attribute**. Defaults to WGS84.

    """

    input: str = attr.ib()
    mosaic_def: MosaicJSON = attr.ib(default=None, converter=_convert_to_mosaicjson)

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=None)
    maxzoom: int = attr.ib(default=None)

    reader: Union[
        Type[BaseReader],
        Type[MultiBaseReader],
        Type[MultiBandReader],
    ] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    bounds: Tuple[float, float, float, float] = attr.ib(
        init=False, default=(-180, -90, 180, 90)
    )
    crs: CRS = attr.ib(init=False, default=WGS84_CRS)
    geographic_crs: CRS = attr.ib(init=False, default=WGS84_CRS)

    _backend_name: str
    _file_byte_size: Optional[int] = 0

    def __attrs_post_init__(self):
        """Post Init: if not passed in init, try to read from self.input."""
        self.mosaic_def = self.mosaic_def or self._read()
        self.bounds = self.mosaic_def.bounds

        # in order to keep support for old mosaic document we assume the default TMS to be WebMercatorQuad
        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS

        # By mosaic definition, its `bounds` is defined using the mosaic's TMS
        # Geographic CRS so we define both `crs` and `geographic_crs` using the mosaic
        # TMS geographic_crs.
        self.crs = mosaic_tms.rasterio_geographic_crs
        self.geographic_crs = mosaic_tms.rasterio_geographic_crs

        # if we open the Mosaic with a TMS which is not the mosaic TMS
        # the min/max zoom will default to the TMS (read) zooms
        # except if min/max zoom are passed by the user
        if self.minzoom is None:
            self.minzoom = (
                self.mosaic_def.minzoom if mosaic_tms == self.tms else self.tms.minzoom
            )

        if self.maxzoom is None:
            self.maxzoom = (
                self.mosaic_def.maxzoom if mosaic_tms == self.tms else self.tms.maxzoom
            )

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
            tilematrixset=self.mosaic_def.tilematrixset,
            quiet=quiet,
            **kwargs,
        )

        for quadkey, new_assets in new_mosaic.tiles.items():
            mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS
            tile = mosaic_tms.quadkey_to_tile(quadkey)
            assets = self.assets_for_tile(*tile)
            assets = [*new_assets, *assets] if add_first else [*assets, *new_assets]

            # add custom sorting algorithm (e.g based on path name)
            self.mosaic_def.tiles[quadkey] = assets

        bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)

        if self.mosaic_def.mosaicjson != new_mosaic.mosaicjson:
            warnings.warn(
                f"Updating `mosaicjson` version from {self.mosaic_def.mosaicjson} to {new_mosaic.mosaicjson}"
            )
            self.mosaic_def.mosaicjson = new_mosaic.mosaicjson

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
        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS
        if self.tms == mosaic_tms:
            return self.get_assets(x, y, z)

        # If TMS are different, then use Tile's geographic coordinates
        # and `assets_for_bbox` to get the assets
        xmin, ymin, xmax, ymax = self.tms.bounds(x, y, z)
        return self.assets_for_bbox(
            xmin,
            ymin,
            xmax,
            ymax,
            coord_crs=self.tms.rasterio_geographic_crs,
        )

    def assets_for_point(
        self,
        lng: float,
        lat: float,
        coord_crs: Optional[CRS] = None,
    ) -> List[str]:
        """Retrieve assets for point."""
        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS
        # default coord_crs should be the TMS's geographic CRS
        coord_crs = coord_crs or self.tms.rasterio_geographic_crs
        # If coord_crs is not the same as the mosaic's geographic CRS
        # we reproject the coordinates
        if coord_crs != mosaic_tms.rasterio_geographic_crs:
            xs, ys = transform(
                coord_crs, mosaic_tms.rasterio_geographic_crs, [lng], [lat]
            )
            lng, lat = xs[0], ys[0]

        # Find the tile index using geographic coordinates
        tile = mosaic_tms.tile(lng, lat, self.quadkey_zoom)

        return self.get_assets(tile.x, tile.y, tile.z)

    def assets_for_bbox(
        self,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        coord_crs: Optional[CRS] = None,
    ) -> List[str]:
        """Retrieve assets for bbox."""
        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS
        # default coord_crs should be the TMS's geographic CRS
        coord_crs = coord_crs or self.tms.rasterio_geographic_crs
        # If coord_crs is not the same as the mosaic's geographic CRS
        # we reproject the bounding box
        if coord_crs != mosaic_tms.rasterio_geographic_crs:
            xmin, ymin, xmax, ymax = transform_bounds(
                coord_crs,
                mosaic_tms.rasterio_geographic_crs,
                xmin,
                ymin,
                xmax,
                ymax,
            )

        tl_tile = mosaic_tms.tile(xmin, ymax, self.quadkey_zoom)
        br_tile = mosaic_tms.tile(xmax, ymin, self.quadkey_zoom)

        tiles = [
            (x, y, self.quadkey_zoom)
            for x in range(tl_tile.x, br_tile.x + 1)
            for y in range(tl_tile.y, br_tile.y + 1)
        ]

        return list(
            dict.fromkeys(
                itertools.chain.from_iterable([self.get_assets(*t) for t in tiles])
            )
        )

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self, x, y, z: hashkey(self.input, x, y, z, self.mosaicid),
    )
    def get_assets(self, x: int, y: int, z: int) -> List[str]:
        """Find assets."""
        quadkeys = self.find_quadkeys(Tile(x=x, y=y, z=z), self.quadkey_zoom)
        assets = list(
            dict.fromkeys(
                itertools.chain.from_iterable(
                    [self.mosaic_def.tiles.get(qk, []) for qk in quadkeys]
                )
            )
        )
        if self.mosaic_def.asset_prefix:
            assets = [self.mosaic_def.asset_prefix + asset for asset in assets]

        return assets

    def find_quadkeys(self, tile: Tile, quadkey_zoom: int) -> List[str]:
        """
        Find quadkeys at desired zoom for tile

        Attributes
        ----------
        tile: morecantile.Tile
            Input tile to use when searching for quadkeys
        quadkey_zoom: int
            Zoom level

        Returns
        -------
        list
            List[str] of quadkeys

        """
        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS

        # get parent
        if tile.z > quadkey_zoom:
            depth = tile.z - quadkey_zoom
            for _ in range(depth):
                tile = mosaic_tms.parent(tile)[0]

            return [mosaic_tms.quadkey(*tile)]

        # get child
        elif tile.z < quadkey_zoom:
            depth = quadkey_zoom - tile.z

            tiles = [tile]
            for _ in range(depth):
                tiles = sum([mosaic_tms.children(t) for t in tiles], [])

            tiles = list(filter(lambda t: t.z == quadkey_zoom, tiles))
            return [mosaic_tms.quadkey(*tile) for tile in tiles]

        else:
            return [mosaic_tms.quadkey(*tile)]

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
            with self.reader(asset, tms=self.tms, **self.reader_options) as src_dst:
                return src_dst.tile(x, y, z, **kwargs)

        return mosaic_reader(mosaic_assets, _reader, x, y, z, **kwargs)

    def point(
        self,
        lon: float,
        lat: float,
        coord_crs: Optional[CRS] = None,
        reverse: bool = False,
        **kwargs: Any,
    ) -> List[PointData]:
        """Get Point value from multiple observation."""
        # default coord_crs should be the TMS's geographic CRS
        coord_crs = coord_crs or self.tms.rasterio_geographic_crs
        mosaic_assets = self.assets_for_point(lon, lat, coord_crs=coord_crs)
        if not mosaic_assets:
            raise NoAssetFoundError(f"No assets found for point ({lon},{lat})")

        if reverse:
            mosaic_assets = list(reversed(mosaic_assets))

        def _reader(
            asset: str, lon: float, lat: float, coord_crs: CRS, **kwargs
        ) -> PointData:
            with self.reader(asset, **self.reader_options) as src_dst:
                return src_dst.point(lon, lat, coord_crs=coord_crs, **kwargs)

        if "allowed_exceptions" not in kwargs:
            kwargs.update({"allowed_exceptions": (PointOutsideBounds,)})

        return list(
            multi_values(mosaic_assets, _reader, lon, lat, coord_crs, **kwargs).items()
        )

    def info(self, quadkeys: bool = False) -> Info:  # type: ignore
        """Mosaic info."""
        return Info(
            bounds=self.geographic_bounds,
            center=self.center,
            maxzoom=self.maxzoom,
            minzoom=self.minzoom,
            name=self.mosaic_def.name if self.mosaic_def.name else "mosaic",
            quadkeys=[] if not quadkeys else self._quadkeys,
            tilematrixset=repr(self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS),
        )

    @property
    def center(self):
        """Return center from the mosaic definition."""
        return (
            (self.bounds[0] + self.bounds[2]) / 2,
            (self.bounds[1] + self.bounds[3]) / 2,
            self.minzoom,
        )

    @property
    def mosaicid(self) -> str:
        """Return sha224 id of the mosaicjson document."""
        return get_hash(**self.mosaic_def.model_dump(exclude_none=True))

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
