"""cogeo_mosaic.mosaic MosaicJSON models and helper functions."""

import os
import re
import sys
import warnings
from contextlib import ExitStack
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import click
import morecantile
from pydantic import BaseModel, Field, field_validator, model_validator
from shapely import linearrings, polygons, total_bounds
from shapely.strtree import STRtree
from supermorecado import burnTiles

from cogeo_mosaic.errors import MosaicError, MultipleDataTypeError
from cogeo_mosaic.utils import _intersect_percent, get_footprints

WEB_MERCATOR_TMS = morecantile.tms.get("WebMercatorQuad")


def default_accessor(feature: Dict) -> str:
    """Return specific feature identifier."""
    return feature["properties"]["path"]


def default_filter(
    tile: morecantile.Tile,
    dataset: Sequence[Dict],
    geoms: Sequence[polygons],
    minimum_tile_cover: float = None,
    tile_cover_sort: bool = False,
    maximum_items_per_tile: Optional[int] = None,
) -> List:
    """Filter and/or sort dataset per intersection coverage."""
    indices = list(range(len(dataset)))

    if minimum_tile_cover or tile_cover_sort:
        tile_geom = polygons(WEB_MERCATOR_TMS.feature(tile)["geometry"]["coordinates"][0])
        int_pcts = _intersect_percent(tile_geom, geoms)

        if minimum_tile_cover:
            if minimum_tile_cover > 1.0:
                raise MosaicError("`minimum_tile_cover` HAS TO be between 0 and 1.")

            indices = [ind for ind in indices if int_pcts[ind] > minimum_tile_cover]

        if tile_cover_sort:
            # https://stackoverflow.com/a/9764364
            _, indices = zip(*sorted(zip(int_pcts, indices), reverse=True))  # type: ignore

    if maximum_items_per_tile:
        indices = indices[:maximum_items_per_tile]

    return [dataset[ind] for ind in indices]


class MosaicJSON(BaseModel, validate_assignment=True):
    """MosaicJSON model.

    Based on https://github.com/developmentseed/mosaicjson-spec

    """

    mosaicjson: str
    name: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    attribution: Optional[str] = None
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    quadkey_zoom: Optional[int] = None
    bounds: Tuple[float, float, float, float] = Field(default=(-180, -90, 180, 90))
    center: Optional[Tuple[float, float, int]] = None
    tiles: Dict[str, List[str]]
    tilematrixset: Optional[morecantile.TileMatrixSet] = None
    asset_type: Optional[str] = None
    asset_prefix: Optional[str] = None
    data_type: Optional[str] = None
    colormap: Optional[Dict[int, Tuple[int, int, int, int]]] = None
    layers: Optional[Dict] = None

    @field_validator("tilematrixset")
    def parse_tms(cls, value) -> Optional[morecantile.TileMatrixSet]:
        """Parse TMS."""
        if value:
            value = morecantile.TileMatrixSet.model_validate(value)
            assert value.is_quadtree, f"{value.id} TMS does not support quadtree."

        return value

    @model_validator(mode="after")
    def compute_center(self):
        """Compute center if it does not exist."""
        bounds = self.bounds
        if not self.center:
            self.center = (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
                self.minzoom,
            )
        return self

    def _increase_version(self):
        """Increment mosaicjson document version."""
        version = list(map(int, self.version.split(".")))
        version[-1] += 1
        new_version = ".".join(map(str, version))
        self.version = new_version

    @classmethod
    def _create_mosaic(
        cls,
        features: Sequence[Dict],
        minzoom: int,
        maxzoom: int,
        quadkey_zoom: Optional[int] = None,
        accessor: Callable[[Dict], str] = default_accessor,
        asset_filter: Callable = default_filter,
        version: str = "0.0.3",
        tilematrixset: Optional[morecantile.TileMatrixSet] = None,
        asset_type: Optional[str] = None,
        asset_prefix: Optional[str] = None,
        data_type: Optional[str] = None,
        colormap: Optional[Dict[int, Tuple[int, int, int, int]]] = None,
        layers: Optional[Dict] = None,
        quiet: bool = True,
        **kwargs,
    ):
        """Create mosaic definition content.

        Attributes:
            features (list): List of GeoJSON features.
            minzoom (int): Force mosaic min-zoom.
            maxzoom (int): Force mosaic max-zoom.
            quadkey_zoom (int): Force mosaic quadkey zoom (optional).
            accessor (callable): Function called on each feature to get its identifier (default is feature["properties"]["path"]).
            asset_filter (callable):  Function to filter features.
            version (str): mosaicJSON definition version (default: 0.0.2).
            quiet (bool): Mask processing steps (default is True).
            kwargs (any): Options forwarded to `asset_filter`

        Returns:
            mosaic_definition (MosaicJSON): Mosaic definition.

        Examples:
            >>> MosaicJSON._create_mosaic([], 12, 14)

        """
        tms = tilematrixset or WEB_MERCATOR_TMS

        assert tms.is_quadtree, f"{tms.id} TMS does not support quadtree."

        quadkey_zoom = quadkey_zoom or minzoom

        if not quiet:
            click.echo(f"Get quadkey list for zoom: {quadkey_zoom}", err=True)

        dataset_geoms = polygons(
            [linearrings(feat["geometry"]["coordinates"][0]) for feat in features]
        )

        bounds = tuple(total_bounds(dataset_geoms))

        burntiles = burnTiles(tms=tms)
        tiles = [morecantile.Tile(*t) for t in burntiles.burn(features, quadkey_zoom)]

        mosaic_definition: Dict[str, Any] = {
            "mosaicjson": version,
            "minzoom": minzoom,
            "maxzoom": maxzoom,
            "quadkey_zoom": quadkey_zoom,
            "bounds": bounds,
            "center": (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
                minzoom,
            ),
            "tiles": {},
            "version": "1.0.0",
        }

        mosaic_003 = {
            "tilematrixset": tilematrixset,
            "asset_type": asset_type,
            "asset_prefix": asset_prefix,
            "data_type": data_type,
            "colormap": colormap,
            "layers": layers,
        }
        for k, v in mosaic_003.items():
            if v is not None:
                mosaic_definition[k] = v

        if not quiet:
            click.echo("Feed Quadkey index", err=True)

        # Create tree and find assets that overlap each tile
        tree = STRtree(dataset_geoms)

        with ExitStack() as ctx:
            fout = ctx.enter_context(open(os.devnull, "w")) if quiet else sys.stderr
            with click.progressbar(  # type: ignore
                tiles, file=fout, show_percent=True, label="Iterate over quadkeys"
            ) as bar:
                for tile in bar:
                    quadkey = tms.quadkey(tile)
                    tile_geom = polygons(tms.feature(tile)["geometry"]["coordinates"][0])

                    # Find intersections from rtree
                    intersections_idx = sorted(
                        tree.query(tile_geom, predicate="intersects")
                    )
                    if len(intersections_idx) == 0:
                        continue

                    intersect_dataset, intersect_geoms = zip(
                        *[
                            (features[idx], dataset_geoms[idx])
                            for idx in intersections_idx
                        ]
                    )

                    dataset = asset_filter(
                        tile, intersect_dataset, intersect_geoms, **kwargs
                    )

                    if dataset:
                        assets = [accessor(f) for f in dataset]
                        if asset_prefix:
                            assets = [
                                re.sub(rf"^{asset_prefix}", "", asset)
                                if asset.startswith(asset_prefix)
                                else asset
                                for asset in assets
                            ]

                        mosaic_definition["tiles"][quadkey] = assets

        return cls(**mosaic_definition)

    @classmethod
    def from_urls(
        cls,
        urls: Sequence[str],
        minzoom: Optional[int] = None,
        maxzoom: Optional[int] = None,
        max_threads: int = 20,
        tilematrixset: Optional[morecantile.TileMatrixSet] = None,
        quiet: bool = True,
        **kwargs,
    ):
        """Create mosaicjson from COG urls.

        Attributes:
            urls (list): List of COGs.
            tilematrixset: (morecantile.TileMatrixSet), optional (default: "WebMercatorQuad")
            minzoom (int): Force mosaic min-zoom.
            maxzoom (int): Force mosaic max-zoom.
            max_threads (int): Max threads to use (default: 20).
            quiet (bool): Mask processing steps (default is True).
            kwargs (any): Options forwarded to `MosaicJSON._create_mosaic`

        Returns:
            mosaic_definition (MosaicJSON): Mosaic definition.


        Raises:
            Exception: If COGs don't have the same datatype

        Examples:
            >>> MosaicJSON.from_urls(["1.tif", "2.tif"])

        """
        features = get_footprints(
            urls, max_threads=max_threads, tms=tilematrixset, quiet=quiet
        )

        if minzoom is None:
            data_minzoom = {feat["properties"]["minzoom"] for feat in features}
            if len(data_minzoom) > 1:
                warnings.warn(
                    "Multiple MinZoom, Assets different minzoom values", UserWarning
                )

            minzoom = max(data_minzoom)

        if maxzoom is None:
            data_maxzoom = {feat["properties"]["maxzoom"] for feat in features}
            if len(data_maxzoom) > 1:
                warnings.warn(
                    "Multiple MaxZoom, Assets have multiple resolution values",
                    UserWarning,
                )

            maxzoom = max(data_maxzoom)

        datatype = {feat["properties"]["datatype"] for feat in features}
        if len(datatype) > 1:
            raise MultipleDataTypeError("Dataset should have the same data type")

        return cls._create_mosaic(
            features,
            minzoom=minzoom,
            maxzoom=maxzoom,
            tilematrixset=tilematrixset,
            quiet=quiet,
            **kwargs,
        )

    @classmethod
    def from_features(
        cls, features: Sequence[Dict], minzoom: int, maxzoom: int, **kwargs
    ):
        """Create mosaicjson from a set of GeoJSON Features.

        Attributes:
            features (list): List of GeoJSON features.
            minzoom (int): Force mosaic min-zoom.
            maxzoom (int): Force mosaic max-zoom.
            kwargs (any): Options forwarded to `MosaicJSON._create_mosaic`

        Returns:
            mosaic_definition (MosaicJSON): Mosaic definition.

        Examples:
            >>> MosaicJSON.from_features([{}, {}], 12, 14)

        """
        return cls._create_mosaic(features, minzoom, maxzoom, **kwargs)
