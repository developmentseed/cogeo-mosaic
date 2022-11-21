"""cogeo_mosaic.mosaic MosaicJSON models and helper functions."""

import os
import sys
import warnings
from contextlib import ExitStack
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import click
import morecantile
from pydantic import BaseModel, Field, root_validator
from shapely import linearrings, polygons, total_bounds
from shapely.strtree import STRtree
from supermercado import burntiles

from cogeo_mosaic.errors import MosaicError
from cogeo_mosaic.utils import _intersect_percent, get_footprints

tms = morecantile.tms.get("WebMercatorQuad")


def default_accessor(feature: Dict):
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
        tile_geom = polygons(tms.feature(tile)["geometry"]["coordinates"][0])
        int_pcts = _intersect_percent(tile_geom, geoms)

        if minimum_tile_cover:
            if minimum_tile_cover > 1.0:
                raise MosaicError("`minimum_tile_cover` HAS TO be between 0 and 1.")

            indices = [ind for ind in indices if int_pcts[ind] > minimum_tile_cover]

        if tile_cover_sort:
            # https://stackoverflow.com/a/9764364
            _, indices = zip(*sorted(zip(int_pcts, indices), reverse=True))

    if maximum_items_per_tile:
        indices = indices[:maximum_items_per_tile]

    return [dataset[ind] for ind in indices]


class MosaicJSON(BaseModel):
    """MosaicJSON model.

    Based on https://github.com/developmentseed/mosaicjson-spec

    """

    mosaicjson: str
    name: Optional[str]
    description: Optional[str]
    version: str = "1.0.0"
    attribution: Optional[str]
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    quadkey_zoom: Optional[int]
    bounds: Tuple[float, float, float, float] = Field((-180, -90, 180, 90))
    center: Optional[Tuple[float, float, int]]
    tiles: Dict[str, List[str]]

    class Config:
        """Validate model on update."""

        validate_assignment = True

    @root_validator
    def compute_center(cls, values):
        """Compute center if it does not exist."""
        bounds = values["bounds"]
        if not values.get("center"):
            values["center"] = (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
                values["minzoom"],
            )
        return values

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
        version: str = "0.0.2",
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
        quadkey_zoom = quadkey_zoom or minzoom

        if not quiet:
            click.echo(f"Get quadkey list for zoom: {quadkey_zoom}", err=True)

        dataset_geoms = polygons(
            [linearrings(feat["geometry"]["coordinates"][0]) for feat in features]
        )

        bounds = tuple(total_bounds(dataset_geoms))

        tiles = burntiles.burn(features, quadkey_zoom)
        tiles = [morecantile.Tile(*tile) for tile in tiles]

        mosaic_definition: Dict[str, Any] = dict(
            mosaicjson=version,
            minzoom=minzoom,
            maxzoom=maxzoom,
            quadkey_zoom=quadkey_zoom,
            bounds=bounds,
            center=((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, minzoom),
            tiles={},
            version="1.0.0",
        )

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
                    tile_geom = polygons(
                        tms.feature(tile)["geometry"]["coordinates"][0]
                    )

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
                        mosaic_definition["tiles"][quadkey] = [
                            accessor(f) for f in dataset
                        ]

        return cls(**mosaic_definition)

    @classmethod
    def from_urls(
        cls,
        urls: Sequence[str],
        minzoom: Optional[int] = None,
        maxzoom: Optional[int] = None,
        max_threads: int = 20,
        quiet: bool = True,
        **kwargs,
    ):
        """Create mosaicjson from COG urls.

        Attributes:
            urls (list): List of COGs.
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

        features = get_footprints(urls, max_threads=max_threads, quiet=quiet)

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
            raise Exception("Dataset should have the same data type")

        return cls._create_mosaic(
            features, minzoom=minzoom, maxzoom=maxzoom, quiet=quiet, **kwargs
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
