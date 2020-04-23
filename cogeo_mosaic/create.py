"""cogeo_mosaic.create: Create MosaicJSON from features."""

from typing import Dict, Sequence
import warnings

import click
import mercantile
from pygeos import STRtree, polygons, total_bounds
from supermercado import burntiles

from cogeo_mosaic.utils import _filter_and_sort, get_footprints


def create_mosaic(
    dataset_list: Sequence[str],
    minzoom: int = None,
    maxzoom: int = None,
    quadkey_zoom: int = None,
    max_threads: int = 20,
    minimum_tile_cover: float = None,
    tile_cover_sort: bool = False,
    version: str = "0.0.2",
    quiet: bool = True,
) -> Dict:
    """
    Create mosaic definition content.

    Attributes
    ----------
    dataset_list : tuple or list, required
        Dataset urls.
    minzoom: int, optional
        Force mosaic min-zoom.
    maxzoom: int, optional
        Force mosaic max-zoom.
    quadkey_zoom: int, optional
        Force mosaic quadkey zoom.
    minimum_tile_cover: float, optional (default: 0)
        Filter files with low tile intersection coverage.
    tile_cover_sort: bool, optional (default: None)
        Sort intersecting files by coverage.
    max_threads : int
        Max threads to use (default: 20).
    version: str, optional
        mosaicJSON definition version
    quiet: bool, optional (default: True)
        Mask processing steps.

    Returns
    -------
    mosaic_definition : dict
        Mosaic definition.

    """
    if version not in ["0.0.1", "0.0.2"]:
        raise Exception(f"Invalid mosaicJSON's version: {version}")

    if not quiet:
        click.echo("Get files footprint", err=True)

    results = get_footprints(dataset_list, max_threads=max_threads, quiet=quiet)

    if minzoom is None:
        minzoom = list(set([feat["properties"]["minzoom"] for feat in results]))
        if len(minzoom) > 1:
            warnings.warn(
                "Multiple MinZoom, Assets different minzoom values", UserWarning
            )

        minzoom = max(minzoom)

    if maxzoom is None:
        maxzoom = list(set([feat["properties"]["maxzoom"] for feat in results]))
        if len(maxzoom) > 1:
            warnings.warn(
                "Multiple MaxZoom, Assets have multiple resolution values", UserWarning
            )

        maxzoom = max(maxzoom)

    quadkey_zoom = quadkey_zoom or minzoom

    datatype = list(set([feat["properties"]["datatype"] for feat in results]))
    if len(datatype) > 1:
        raise Exception("Dataset should have the same data type")

    if not quiet:
        click.echo(f"Get quadkey list for zoom: {quadkey_zoom}", err=True)

    # Find dataset geometries
    dataset_geoms = polygons([feat["geometry"]["coordinates"][0] for feat in results])
    bounds = list(total_bounds(dataset_geoms))

    tiles = burntiles.burn(results, quadkey_zoom)
    tiles = [mercantile.Tile(*tile) for tile in tiles]

    mosaic_definition = dict(
        mosaicjson=version,
        minzoom=minzoom,
        maxzoom=maxzoom,
        bounds=bounds,
        center=[(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2, minzoom],
        tiles={},
        version="1.0.0",
    )

    if version == "0.0.2":
        mosaic_definition.update(dict(quadkey_zoom=quadkey_zoom))

    if not quiet:
        click.echo(f"Feed Quadkey index", err=True)

    # Create tree and find assets that overlap each tile
    tree = STRtree(dataset_geoms)

    for tile in tiles:
        quadkey = mercantile.quadkey(tile)
        tile_geom = polygons(mercantile.feature(tile)["geometry"]["coordinates"][0])

        # Find intersections from rtree
        intersections_idx = sorted(tree.query(tile_geom, predicate="intersects"))
        if len(intersections_idx) == 0:
            continue

        intersections_geoms = [dataset_geoms[idx] for idx in intersections_idx]
        intersections = [results[idx] for idx in intersections_idx]

        dataset = [
            {"path": f["properties"]["path"], "geometry": geom}
            for (f, geom) in zip(intersections, intersections_geoms)
        ]

        if minimum_tile_cover is not None or tile_cover_sort:
            dataset = _filter_and_sort(
                tile_geom,
                dataset,
                minimum_cover=minimum_tile_cover,
                sort_cover=tile_cover_sort,
            )

        if dataset:
            mosaic_definition["tiles"][quadkey] = [f["path"] for f in dataset]

    return mosaic_definition
