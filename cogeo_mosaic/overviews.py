"""cogeo_mosaic.overviews: create low resolution image from a mosaic."""

import random
from concurrent import futures
from contextlib import ExitStack
from typing import Any, Dict, List, Tuple

import click
import mercantile
import numpy
import rasterio
from affine import Affine
from rasterio.io import MemoryFile
from rasterio.rio.overview import get_maximum_overview_level
from rasterio.shutil import copy
from rasterio.windows import Window
from rio_cogeo.cogeo import TemporaryRasterFile
from rio_cogeo.utils import _meters_per_pixel
from rio_tiler.io import COGReader
from rio_tiler.mosaic.methods import defaults
from supermercado.burntiles import tile_extrema

from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.backends.utils import find_quadkeys
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.utils import _filter_futures

PIXSEL_METHODS = {
    "first": defaults.FirstMethod,
    "highest": defaults.HighestMethod,
    "lowest": defaults.LowestMethod,
    "mean": defaults.MeanMethod,
    "median": defaults.MedianMethod,
    "stdev": defaults.StdevMethod,
}


def _tile(
    src_path: str, *args: Any, **kwargs: Any
) -> Tuple[numpy.ndarray, numpy.ndarray]:
    with COGReader(src_path) as cog:
        return cog.tile(*args, **kwargs)


def _get_info(src_path: str) -> Dict:
    with COGReader(src_path) as cog:
        info = cog.info()
        info["nodata_value"] = cog.dataset.nodata

    return info


def _split_extrema(extrema: Dict, max_ovr: int = 6) -> List[Dict]:
    """Create multiple extremas."""
    nb_ovrtile = 2 ** max_ovr
    extr = []
    for x in range(extrema["x"]["min"], extrema["x"]["max"], nb_ovrtile):
        maxx = min(x + nb_ovrtile, extrema["x"]["max"])
        for y in range(extrema["y"]["min"], extrema["y"]["max"], nb_ovrtile):
            maxy = min(y + nb_ovrtile, extrema["y"]["max"])

            extr.append({"x": {"min": x, "max": maxx}, "y": {"min": y, "max": maxy}})

    return extr


def _get_blocks(extrema: Dict, tilesize: int = 256):
    for j in range(extrema["y"]["max"] - extrema["y"]["min"]):
        row = j * tilesize
        for i in range(extrema["x"]["max"] - extrema["x"]["min"]):
            col = i * tilesize

            yield (j, i), Window(
                col_off=col, row_off=row, width=tilesize, height=tilesize
            )


def create_overview_cogs(
    mosaic_path: str,
    output_profile: Dict,
    prefix: str = "mosaic_ovr",
    max_overview_level: int = 6,
    method: str = "first",
    config: Dict = None,
    threads=1,
    in_memory: bool = True,
) -> None:
    """
    Create Low resolution mosaic image from a mosaicJSON.

    The output will be a web optimized COG with bounds matching the mosaicJSON bounds and
    with its resolution matching the mosaic MinZoom - 1.

    Attributes
    ----------
    mosaic_path : str, required
        Mosaic definition path.
    output_profile : dict, required
    prefix : str
    max_overview_level : int
    method: str, optional
        pixel_selection method name (default is 'first').
    config : dict
        Rasterio Env options.
    threads: int, optional
        maximum number of threads to use (default is 1).
    in_memory: bool, optional
        Force COG creation in memory (default is True).

    """
    pixel_method = PIXSEL_METHODS[method]

    with MosaicBackend(mosaic_path) as mosaic:
        base_zoom = mosaic.metadata["minzoom"] - 1
        mosaic_quadkey_zoom = mosaic.quadkey_zoom
        bounds = mosaic.metadata["bounds"]
        mosaic_quadkeys = set(mosaic._quadkeys)

        # Select a random quakey/asset and get dataset info
        tile = mercantile.quadkey_to_tile(random.sample(mosaic_quadkeys, 1)[0])
        assets = mosaic.assets_for_tile(*tile)
        info = _get_info(assets[0])

        extrema = tile_extrema(bounds, base_zoom)
        tilesize = 256
        resolution = _meters_per_pixel(base_zoom, 0, tilesize=tilesize)

        # Create multiples files if coverage is too big
        extremas = _split_extrema(extrema, max_ovr=max_overview_level)
        for ix, extrema in enumerate(extremas):
            click.echo(f"Part {1 + ix}/{len(extremas)}", err=True)
            output_path = f"{prefix}_{ix}.tif"

            blocks = list(_get_blocks(extrema, tilesize))
            random.shuffle(blocks)

            width = (extrema["x"]["max"] - extrema["x"]["min"]) * tilesize
            height = (extrema["y"]["max"] - extrema["y"]["min"]) * tilesize
            w, n = mercantile.xy(
                *mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], base_zoom)
            )

            params = dict(
                driver="GTiff",
                dtype=info["dtype"],
                count=len(info["band_descriptions"]),
                width=width,
                height=height,
                crs="epsg:3857",
                transform=Affine(resolution, 0, w, 0, -resolution, n),
                nodata=info["nodata_value"],
            )
            params.update(**output_profile)

            config = config or {}
            with rasterio.Env(**config):
                with ExitStack() as ctx:
                    if in_memory:
                        tmpfile = ctx.enter_context(MemoryFile())
                        tmp_dst = ctx.enter_context(tmpfile.open(**params))
                    else:
                        tmpfile = ctx.enter_context(TemporaryRasterFile(output_path))
                        tmp_dst = ctx.enter_context(
                            rasterio.open(tmpfile.name, "w", **params)
                        )

                    def _get_tile(wind):
                        idx, window = wind
                        x = extrema["x"]["min"] + idx[1]
                        y = extrema["y"]["min"] + idx[0]
                        t = mercantile.Tile(x, y, base_zoom)

                        kds = set(find_quadkeys(t, mosaic_quadkey_zoom))
                        if not mosaic_quadkeys.intersection(kds):
                            return window, None, None

                        try:
                            (tile, mask), _ = mosaic.tile(
                                t.x,
                                t.y,
                                t.z,
                                tilesize=tilesize,
                                pixel_selection=pixel_method(),
                            )
                        except NoAssetFoundError:
                            return window, None, None

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
                        if tile is None:
                            continue

                        tmp_dst.write(tile, window=window)
                        if info["nodata_type"] == "Mask":
                            tmp_dst.write_mask(mask.astype("uint8"), window=window)

                    min_tile_size = tilesize = min(
                        int(output_profile["blockxsize"]),
                        int(output_profile["blockysize"]),
                    )
                    overview_level = get_maximum_overview_level(
                        tmp_dst.width, tmp_dst.height, minsize=min_tile_size
                    )
                    overviews = [2 ** j for j in range(1, overview_level + 1)]
                    tmp_dst.build_overviews(overviews)
                    copy(tmp_dst, output_path, copy_src_overviews=True, **params)
