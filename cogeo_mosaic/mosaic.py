"""cogeo_mosaic.mosaic MosaicJSON models and helper functions."""

import warnings
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import click
import mercantile
from pydantic import BaseModel, Field, root_validator
from pygeos import STRtree, polygons, total_bounds
from supermercado import burntiles

from cogeo_mosaic.utils import _intersect_percent, get_footprints


def default_accessor(feature: Dict):
    """Return specific feature identifier."""
    return feature["properties"]["path"]


def default_filter(
    tile: mercantile.Tile,
    dataset: Sequence[Dict],
    geoms: Sequence[polygons],
    minimum_tile_cover=None,
    tile_cover_sort=False,
    maximum_items_per_tile: Optional[int] = None,
) -> List:
    """Filter and/or sort dataset per intersection coverage."""
    indices = list(range(len(dataset)))

    if minimum_tile_cover or tile_cover_sort:
        tile_geom = polygons(mercantile.feature(tile)["geometry"]["coordinates"][0])
        int_pcts = _intersect_percent(tile_geom, geoms)

        if minimum_tile_cover:
            indices = [ind for ind in indices if int_pcts[ind] > minimum_tile_cover]

        if tile_cover_sort:
            # https://stackoverflow.com/a/9764364
            indices, _ = zip(*sorted(zip(indices, int_pcts), reverse=True))

    if maximum_items_per_tile:
        indices = indices[:maximum_items_per_tile]

    return [dataset[ind] for ind in indices]


class MosaicJSON(BaseModel):
    """
    MosaicJSON model.

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
    bounds: List[float] = Field([-180, -90, 180, 90])
    center: Optional[Tuple[float, float, int]]
    tiles: Dict[str, List[str]]

    class Config:
        """Validate model on update."""

        validate_assignment = True

    @root_validator(pre=True)
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
        """
        Create mosaic definition content.

        Attributes
        ----------
        features : List, required
            List of GeoJSON features.
        minzoom: int, required
            Force mosaic min-zoom.
        maxzoom: int, required
            Force mosaic max-zoom.
        quadkey_zoom: int, optional
            Force mosaic quadkey zoom.
        accessor: callable, required
            Function called on each feature to get its identifier (default is feature["properties"]["path"]).
        asset_filter: callable, required
            Function to filter features.
        version: str, optional
            mosaicJSON definition version (default: 0.0.2).
        quiet: bool, optional (default: True)
            Mask processing steps.
        kwargs: any
            Options forwarded to `asset_filter`

        Returns
        -------
        mosaic_definition : MosaicJSON
            Mosaic definition.

        """
        quadkey_zoom = quadkey_zoom or minzoom

        if not quiet:
            click.echo(f"Get quadkey list for zoom: {quadkey_zoom}", err=True)

        # If Pygeos throws an error, fall back to non-vectorized operation
        # Ref: https://github.com/developmentseed/cogeo-mosaic/issues/81
        try:
            dataset_geoms = polygons(
                [feat["geometry"]["coordinates"][0] for feat in features]
            )
        except TypeError:
            dataset_geoms = [
                polygons(feat["geometry"]["coordinates"][0]) for feat in features
            ]

        bounds = list(total_bounds(dataset_geoms))

        tiles = burntiles.burn(features, quadkey_zoom)
        tiles = [mercantile.Tile(*tile) for tile in tiles]

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

        for tile in tiles:
            quadkey = mercantile.quadkey(tile)
            tile_geom = polygons(mercantile.feature(tile)["geometry"]["coordinates"][0])

            # Find intersections from rtree
            intersections_idx = sorted(tree.query(tile_geom, predicate="intersects"))
            if len(intersections_idx) == 0:
                continue

            intersect_dataset, intersect_geoms = zip(
                *[(features[idx], dataset_geoms[idx]) for idx in intersections_idx]
            )

            dataset = asset_filter(tile, intersect_dataset, intersect_geoms, **kwargs)

            if dataset:
                mosaic_definition["tiles"][quadkey] = [accessor(f) for f in dataset]

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
        """
        Create mosaicjson from COG urls.

        Attributes
        ----------
        urls : List, required
            List of COG urls.
        minzoom: int, optional
            Force mosaic min-zoom.
        maxzoom: int, optional
            Force mosaic max-zoom.
        max_threads : int
            Max threads to use (default: 20).
        quiet: bool, optional (default: True)
            Mask processing steps.
        kwargs: any
            Options forwarded to MosaicJSON.from_features

        Returns
        -------
        mosaic_definition : MosaicJSON
            Mosaic definition.

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
        """
        Create mosaicjson from a set of GeoJSON Features.

        Attributes
        ----------
        features: list, required
            List of GeoJSON features.
        minzoom: int, required
            Force mosaic min-zoom.
        maxzoom: int, required
            Force mosaic max-zoom.
        kwargs: any
            Options forwarded to MosaicJSON._create_mosaic

        Returns
        -------
        mosaic_definition : MosaicJSON
            Mosaic definition.

        """
        return cls._create_mosaic(features, minzoom, maxzoom, **kwargs)
