"""cogeo_mosaic.utils: utility functions."""

import logging
import os
import sys
from concurrent import futures
from contextlib import ExitStack
from typing import Dict, List, Sequence, Tuple

import click
import morecantile
import numpy
from rio_tiler.io import Reader
from shapely import area, intersection

logger = logging.getLogger()
logger.setLevel(logging.INFO)

tms = morecantile.tms.get("WebMercatorQuad")


def _filter_futures(tasks):
    """
    Filter future task to remove Exceptions.

    Attributes
    ----------
    tasks : list
        List of 'concurrent.futures._base.Future'

    Yields
    ------
    Successful task's result

    """
    for future in tasks:
        try:
            yield future.result()
        except Exception as err:
            logger.warning(str(err))
            pass


def get_dataset_info(src_path: str) -> Dict:
    """Get rasterio dataset meta."""
    with Reader(src_path) as src:
        bounds = src.geographic_bounds
        return {
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [bounds[0], bounds[3]],
                        [bounds[0], bounds[1]],
                        [bounds[2], bounds[1]],
                        [bounds[2], bounds[3]],
                        [bounds[0], bounds[3]],
                    ]
                ],
            },
            "properties": {
                "path": src_path,
                "bounds": bounds,
                "minzoom": src.minzoom,
                "maxzoom": src.maxzoom,
                "datatype": src.dataset.meta["dtype"],
            },
            "type": "Feature",
        }


def get_footprints(
    dataset_list: Sequence[str], max_threads: int = 20, quiet: bool = True
) -> List:
    """
    Create footprint GeoJSON.

    Attributes
    ----------
    dataset_listurl : tuple or list, required
        Dataset urls.
    max_threads : int
        Max threads to use (default: 20).

    Returns
    -------
    out : tuple
        tuple of footprint feature.

    """
    with ExitStack() as ctx:
        fout = ctx.enter_context(open(os.devnull, "w")) if quiet else sys.stderr
        with futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            future_work = [
                executor.submit(get_dataset_info, item) for item in dataset_list
            ]
            with click.progressbar(  # type: ignore
                futures.as_completed(future_work),
                file=fout,
                length=len(future_work),
                label="Get footprints",
                show_percent=True,
            ) as future:
                for _ in future:
                    pass

    return list(_filter_futures(future_work))


def tiles_to_bounds(tiles: List[morecantile.Tile]) -> Tuple[float, float, float, float]:
    """Get bounds from a set of mercator tiles."""
    zoom = tiles[0].z
    xyz = numpy.array([[t.x, t.y, t.z] for t in tiles])
    extrema = {
        "x": {"min": xyz[:, 0].min(), "max": xyz[:, 0].max() + 1},
        "y": {"min": xyz[:, 1].min(), "max": xyz[:, 1].max() + 1},
    }
    ulx, uly = tms.ul(extrema["x"]["min"], extrema["y"]["min"], zoom)
    lrx, lry = tms.ul(extrema["x"]["max"], extrema["y"]["max"], zoom)
    return (ulx, lry, lrx, uly)


def _intersect_percent(tile, dataset_geoms):
    """Return the overlap percent."""
    inter_areas = area(intersection(tile, dataset_geoms))
    return [inter_area / area(tile) for inter_area in inter_areas]


def bbox_union(
    bbox_1: Tuple[float, float, float, float],
    bbox_2: Tuple[float, float, float, float],
) -> Tuple[float, float, float, float]:
    """Return the union of two bounding boxes."""
    return (
        min(bbox_1[0], bbox_2[0]),
        min(bbox_1[1], bbox_2[1]),
        max(bbox_1[2], bbox_2[2]),
        max(bbox_1[3], bbox_2[3]),
    )
