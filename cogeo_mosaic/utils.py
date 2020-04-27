"""cogeo_mosaic.utils: utility functions."""

from typing import Dict, List, Tuple, Sequence

import os
import sys
import logging
import functools
from concurrent import futures

import click

import numpy
from pygeos import intersection, area
import mercantile

import rasterio
from rio_tiler.mercator import get_zooms
from rasterio.warp import transform_bounds


logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
    with rasterio.open(src_path) as src_dst:
        bounds = transform_bounds(
            src_dst.crs, "epsg:4326", *src_dst.bounds, densify_pts=21
        )
        min_zoom, max_zoom = get_zooms(src_dst, ensure_global_max_zoom=True)
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
                "minzoom": min_zoom,
                "maxzoom": max_zoom,
                "datatype": src_dst.meta["dtype"],
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
    fout = os.devnull if quiet else sys.stderr
    with futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_work = [executor.submit(get_dataset_info, item) for item in dataset_list]
        with click.progressbar(
            futures.as_completed(future_work),
            file=fout,
            length=len(future_work),
            show_percent=True,
        ) as future:
            for res in future:
                pass

    return list(_filter_futures(future_work))


def tiles_to_bounds(tiles: List[mercantile.Tile]) -> List[float]:
    """Get bounds from a set of mercator tiles."""
    zoom = tiles[0].z
    xyz = numpy.array([[t.x, t.y, t.z] for t in tiles])
    extrema = {
        "x": {"min": xyz[:, 0].min(), "max": xyz[:, 0].max() + 1},
        "y": {"min": xyz[:, 1].min(), "max": xyz[:, 1].max() + 1},
    }
    ulx, uly = mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], zoom)
    lrx, lry = mercantile.ul(extrema["x"]["max"], extrema["y"]["max"], zoom)
    return [ulx, lry, lrx, uly]


def get_point_values(assets: Tuple[str], lng: float, lat: float) -> List:
    """Read assets and return point values."""

    def _get_point(asset: str, coordinates: Tuple[float, float]) -> dict:
        with rasterio.open(asset) as src_dst:
            lng_srs, lat_srs = rasterio.warp.transform(
                "epsg:4326", src_dst.crs, [coordinates[0]], [coordinates[1]]
            )

            if not (
                (src_dst.bounds[0] < lng_srs[0] < src_dst.bounds[2])
                and (src_dst.bounds[1] < lat_srs[0] < src_dst.bounds[3])
            ):
                raise Exception("Outside bounds")

            return {
                "asset": asset,
                "values": list(
                    src_dst.sample([(lng_srs[0], lat_srs[0])], indexes=src_dst.indexes)
                )[0].tolist(),
            }

    _points = functools.partial(_get_point, coordinates=[lng, lat])
    with futures.ThreadPoolExecutor() as executor:
        future_work = [executor.submit(_points, item) for item in assets]
        return list(_filter_futures(future_work))


def _intersect_percent(tile, dataset_geoms):
    """Return the overlap percent."""
    inter_areas = area(intersection(tile, dataset_geoms))
    return [inter_area / area(tile) for inter_area in inter_areas]
