"""cogeo_mosaic.utils: utility functions."""

from typing import Dict

import os
import sys
import itertools

import click

import mercantile
from affine import Affine
from supermercado.burntiles import tile_extrema

import rasterio
from rasterio.io import MemoryFile
from rasterio.enums import Resampling as ResamplingEnums
from rasterio.shutil import copy

from rio_tiler.main import tile as cogeoTiler
from rio_tiler_mosaic.mosaic import mosaic_tiler
from rio_tiler_mosaic.methods import defaults

from rio_cogeo.utils import _meters_per_pixel, get_maximum_overview_level

from cogeo_mosaic.utils import get_mosaic_content, get_assets


def _get_info(asset: str) -> Dict:
    with rasterio.open(asset) as dst_src:
        description = [
            dst_src.descriptions[b - 1] for i, b in enumerate(dst_src.indexes)
        ]
        return dst_src.count, dst_src.dtypes[0], description, dst_src.tags()


def _get_asset_example(mosaic_def: Dict) -> str:
    t = list(mosaic_def["tiles"].keys())[0]
    asset = mosaic_def["tiles"][t][0]
    if os.path.splitext(asset)[1] in [".json", ".gz"]:
        mosaic_def = get_mosaic_content(asset)
        return _get_asset_example(mosaic_def)

    return asset


def _split_extrema(extrema: Dict, max_ovr: int = 6, tilesize: int = 256):
    """Create multiple extremas."""
    nb_ovrtile = 2 ** max_ovr
    extr = []
    for idx, x in enumerate(
        range(extrema["x"]["min"], extrema["x"]["max"], nb_ovrtile)
    ):
        for idy, y in enumerate(
            range(extrema["y"]["min"], extrema["y"]["max"], nb_ovrtile)
        ):
            maxx = (
                x + nb_ovrtile
                if x + nb_ovrtile < extrema["x"]["max"]
                else extrema["x"]["max"]
            )
            maxy = (
                y + nb_ovrtile
                if y + nb_ovrtile < extrema["y"]["max"]
                else extrema["y"]["max"]
            )
            extr.append({"x": {"min": x, "max": maxx}, "y": {"min": y, "max": maxy}})
    return extr


def create_low_level_cogs(
    mosaic_definition: Dict,
    dst_kwargs: Dict,
    prefix: str = "mosaic_ovr",
    add_mask: bool = True,
    max_overview_level: int = 6,
    config: Dict = None,
):
    """
    Create WebOptimized Overview COG from a mosaic definition file.

    Attributes
    ----------
    mosaic_definition : dict, required
        Mosaic definition.
    prefix : str
    add_mask, bool, optional
        Force output dataset creation with a mask.
    max_overview_level : int
    config : dict
        Rasterio Env options.

    Returns
    -------

    """
    tilesize = 256

    asset = _get_asset_example(mosaic_definition)
    info = _get_info(asset)

    base_zoom = mosaic_definition["minzoom"] - 1
    bounds = mosaic_definition["bounds"]
    extrema = tile_extrema(bounds, base_zoom)
    res = _meters_per_pixel(base_zoom, 0, tilesize=tilesize)

    # Create multiples files if coverage is too big
    extremas = _split_extrema(extrema, max_ovr=max_overview_level, tilesize=tilesize)
    for ix, extrema in enumerate(extremas):
        width = (extrema["x"]["max"] - extrema["x"]["min"]) * tilesize
        height = (extrema["y"]["max"] - extrema["y"]["min"]) * tilesize
        w, n = mercantile.xy(
            *mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], base_zoom)
        )
        transform = Affine(res, 0, w, 0, -res, n)

        params = dict(
            driver="GTiff",
            count=info[0],
            dtype=info[1],
            crs="epsg:3857",
            transform=transform,
            width=width,
            height=height,
        )

        dst_path = f"{prefix}_{ix}.tif"
        params.update(**dst_kwargs)
        params.pop("compress", None)
        params.pop("photometric", None)

        config = config or {}
        with rasterio.Env(**config):
            with MemoryFile() as memfile:
                with memfile.open(**params) as mem:
                    wind = list(mem.block_windows(1))
                    with click.progressbar(
                        wind,
                        length=len(wind),
                        file=sys.stderr,
                        show_percent=True,
                        label=dst_path,
                    ) as windows:
                        for ij, w in windows:
                            x = extrema["x"]["min"] + ij[1]
                            y = extrema["y"]["min"] + ij[0]
                            tile = mercantile.Tile(x=x, y=y, z=base_zoom)
                            assets = list(
                                itertools.chain.from_iterable(
                                    [
                                        get_assets(mosaic_definition, t.x, t.y, t.z)
                                        for t in mercantile.children(tile)
                                    ]
                                )
                            )
                            assets = list(set(assets))

                            if assets:
                                tile, mask = mosaic_tiler(
                                    assets,
                                    x,
                                    y,
                                    base_zoom,
                                    cogeoTiler,
                                    tilesize=tilesize,
                                    pixel_selection=defaults.FirstMethod(),
                                    resampling_method="bilinear",
                                )

                                mem.write(tile, window=w)
                                if add_mask:
                                    mem.write_mask(mask.astype("uint8"), window=w)

                    overview_level = get_maximum_overview_level(mem, tilesize)

                    overviews = [2 ** j for j in range(1, overview_level + 1)]
                    mem.build_overviews(overviews, ResamplingEnums["nearest"])

                    for i, b in enumerate(mem.indexes):
                        mem.set_band_description(i + 1, info[2][b - 1])

                    tags = info[3]
                    tags.update(
                        dict(OVR_RESAMPLING_ALG=ResamplingEnums["nearest"].name.upper())
                    )
                    mem.update_tags(**tags)

                    copy(mem, dst_path, copy_src_overviews=True, **dst_kwargs)
