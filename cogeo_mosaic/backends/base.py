"""cogeo_mosaic.backend.base: base Backend class."""

from typing import Callable, Dict, List, Sequence

import abc
from contextlib import AbstractContextManager

import mercantile
from pygeos import STRtree, polygons
from supermercado import burntiles

from cogeo_mosaic.utils import tiles_to_bounds
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.backends.utils import get_hash


class BaseBackend(AbstractContextManager):
    """Base Class for cogeo-mosaic backend storage."""

    mosaic_def: MosaicJSON

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
    def tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""

    @abc.abstractmethod
    def point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point."""

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

    @abc.abstractmethod
    def write(self):
        """Upload new MosaicJSON to backend."""

    @abc.abstractmethod
    def update(self):
        """Update existing MosaicJSON on backend."""

    def _update_quadkey(self, quadkey: str, dataset: List[str]):
        """Update quadkey list."""
        self.mosaic_def.tiles[quadkey] = dataset

    def _update_metadata(self, bounds: List[float], version: str):
        """Update bounds and center."""
        self.mosaic_def.version = version
        self.mosaic_def.bounds = bounds
        self.mosaic_def.center = (
            (bounds[0] + bounds[2]) / 2,
            (bounds[1] + bounds[3]) / 2,
            self.mosaic_def.minzoom,
        )

    def _update(
        self,
        features: Sequence[Dict],
        accessor: Callable,
        on_top: bool = True,
        **kwargs
    ):
        """Update existing MosaicJSON on backend."""
        version = self.mosaic_def.version
        if version:
            uversion = list(map(int, version.split(".")))
            uversion[-1] += 1
            version = ".".join(map(str, uversion))
        else:
            version = "1.0.0"

        updated_quadkeys = set()

        dataset_geoms = polygons(
            [feat["geometry"]["coordinates"][0] for feat in features]
        )

        for idx, feature in enumerate(features):
            tiles = burntiles.burn([feature], self.quadkey_zoom)
            tiles = [mercantile.Tile(*tile) for tile in tiles]

            tree = STRtree([dataset_geoms[idx]])

            for tile in tiles:
                quadkey = str(mercantile.quadkey(tile))
                tile_geom = polygons(
                    mercantile.feature(tile)["geometry"]["coordinates"][0]
                )

                # Find intersections from rtree
                intersections_idx = sorted(
                    tree.query(tile_geom, predicate="intersects")
                )
                if len(intersections_idx) == 0:
                    continue

                intersect_dataset, intersect_geoms = zip(
                    *[(features[idx], dataset_geoms[idx]) for idx in intersections_idx]
                )

                dataset = self.mosaic_def._filter(
                    tile, intersect_dataset, intersect_geoms, **kwargs
                )
                new_assets = [accessor(f) for f in dataset]

                assets = self.tile(*tile)
                assets = [*new_assets, *assets] if on_top else [*assets, *new_assets]
                self._update_quadkey(quadkey, assets)

                updated_quadkeys.add(tile)
        bounds = self.mosaic_def.bounds
        minimumTile = mercantile.tile(bounds[0], bounds[3], self.quadkey_zoom)
        maximumTile = mercantile.tile(bounds[2], bounds[1], self.quadkey_zoom)
        bounds = tiles_to_bounds(
            [t for t in updated_quadkeys] + [minimumTile, maximumTile]
        )

        self._update_metadata(bounds, version)

        return
