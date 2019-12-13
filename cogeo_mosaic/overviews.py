"""cogeo_mosaic.utils: utility functions."""

from typing import Dict

import os
import random
from concurrent import futures

import click

import mercantile
from affine import Affine
from supermercado.burntiles import tile_extrema

import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window

from rio_tiler.main import tile as cogeoTiler
from rio_tiler_mosaic.mosaic import mosaic_tiler
from rio_tiler_mosaic.methods import defaults

from rio_cogeo.cogeo import cog_translate
from rio_cogeo.utils import _meters_per_pixel, has_mask_band

from cogeo_mosaic.utils import get_mosaic_content, get_assets, _filter_futures


def _get_info(asset: str) -> Dict:
    with rasterio.open(asset) as src_dst:
        description = [
            src_dst.descriptions[b - 1] for i, b in enumerate(src_dst.indexes)
        ]
        mask = has_mask_band(src_dst)
        return (
            src_dst.count,
            src_dst.dtypes[0],
            description,
            src_dst.tags(),
            src_dst.nodata,
            mask,
        )


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


def _get_blocks(extrema):
    for j in range(extrema["y"]["max"] - extrema["y"]["min"]):
        row = j * 256
        for i in range(extrema["x"]["max"] - extrema["x"]["min"]):
            col = i * 256
            yield (j, i), Window(col_off=col, row_off=row, width=256, height=256)


def create_low_level_cogs(
    mosaic_definition: Dict,
    output_profile: Dict,
    prefix: str = "mosaic_ovr",
    max_overview_level: int = 6,
    config: Dict = None,
    threads=1,
) -> None:
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

    """
    tilesize = 256

    base_zoom = mosaic_definition["minzoom"] - 1
    bounds = mosaic_definition["bounds"]
    asset = _get_asset_example(mosaic_definition)
    info = _get_info(asset)

    extrema = tile_extrema(bounds, base_zoom)
    res = _meters_per_pixel(base_zoom, 0, tilesize=tilesize)

    # Create multiples files if coverage is too big
    extremas = _split_extrema(extrema, max_ovr=max_overview_level, tilesize=tilesize)
    for ix, extrema in enumerate(extremas):
        blocks = list(_get_blocks(extrema))
        random.shuffle(blocks)

        width = (extrema["x"]["max"] - extrema["x"]["min"]) * tilesize
        height = (extrema["y"]["max"] - extrema["y"]["min"]) * tilesize
        w, n = mercantile.xy(
            *mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], base_zoom)
        )

        params = dict(
            driver="GTiff",
            dtype=info[1],
            count=info[0],
            width=width,
            height=height,
            crs="epsg:3857",
            transform=Affine(res, 0, w, 0, -res, n),
            nodata=info[4],
            tiled=True,
            blockxsize=256,
            blockysize=256,
        )

        config = config or {}
        with rasterio.Env(**config):
            with MemoryFile() as memfile:
                with memfile.open(**params) as mem:

                    def _get_tile(wind):
                        idx, window = wind
                        x = extrema["x"]["min"] + idx[1]
                        y = extrema["y"]["min"] + idx[0]
                        assets = list(
                            set(get_assets(mosaic_definition, x, y, base_zoom))
                        )
                        if assets:
                            tile, mask = mosaic_tiler(
                                assets,
                                x,
                                y,
                                base_zoom,
                                cogeoTiler,
                                tilesize=tilesize,
                                pixel_selection=defaults.FirstMethod(),
                            )
                            if tile is None:
                                raise Exception("Empty")

                        return window, tile, mask

                    with futures.ThreadPoolExecutor(max_workers=threads) as executor:
                        future_work = [
                            executor.submit(_get_tile, item) for item in blocks
                        ]
                        with click.progressbar(
                            futures.as_completed(future_work),
                            length=len(future_work),
                            show_percent=True,
                        ) as future:
                            for res in future:
                                pass

                    for f in _filter_futures(future_work):
                        window, tile, mask = f
                        mem.write(tile, window=window)
                        if info[5]:
                            mem.write_mask(mask.astype("uint8"), window=window)

                    cog_translate(
                        mem,
                        f"{prefix}_{ix}.tif",
                        output_profile,
                        config=config,
                        in_memory=True,
                    )
