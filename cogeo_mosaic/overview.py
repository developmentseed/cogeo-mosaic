"""cogeo_mosaic.overviews: create low resolution image from a mosaic."""

import random
import sys
from tempfile import NamedTemporaryFile
from typing import Dict, Optional, Union

import click
import mercantile
import rasterio
from affine import Affine
from mercantile import Tile
from rasterio.windows import Window
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.profiles import cog_profiles
from rio_cogeo.utils import _meters_per_pixel
from rio_tiler.models import ImageData
from rio_tiler.mosaic.methods import defaults
from rio_tiler.mosaic.methods.base import MosaicMethodBase

from cogeo_mosaic.backends import FileBackend
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON

PIXEL_SELECTION_METHODS = {
    "first": defaults.FirstMethod,
    "highest": defaults.HighestMethod,
    "lowest": defaults.LowestMethod,
    "mean": defaults.MeanMethod,
    "median": defaults.MedianMethod,
    "stdev": defaults.StdevMethod,
}


def create_overview_cog(
    mosaic: MosaicJSON,
    output_path: str,
    tilesize: int = 256,
    rasterio_env=None,
    max_overview_level=None,
    pixel_selection_method: Union[str, MosaicMethodBase] = "first",
    output_profile="deflate",
    output_profile_options=None,
):
    """Create overview COG from mosaic
    """
    if type(pixel_selection_method) == str:
        pixel_selection_method = PIXEL_SELECTION_METHODS[pixel_selection_method]

    base_zoom = mosaic.minzoom - 1
    output_base_tiles = list(mercantile.tiles(*mosaic.bounds, base_zoom))
    extrema = tile_extrema(output_base_tiles)

    rasterio_env_kwargs = {} if rasterio_env is None else rasterio_env
    with rasterio.Env(**rasterio_env_kwargs):
        info = get_cog_profile(get_random_asset(mosaic))

    profile = get_output_profile(
        info=info, base_zoom=base_zoom, extrema=extrema, tilesize=tilesize
    )

    with NamedTemporaryFile(suffix=".tif") as tmpf:
        with rasterio.open(tmpf.name, "w", **profile) as rio_tmp:
            # Loop over *output* tiles
            with click.progressbar(
                output_base_tiles,
                show_percent=True,
                label="Loading source tiles",
                file=sys.stderr,
            ) as bar:
                for tile in bar:
                    window = find_window(tile, extrema, tilesize=tilesize)

                    # TODO: how to pass rasterio_env_kwargs? Adding `rasterio.Env`
                    # here doesn't seem to work.
                    data = read_data(
                        tile=tile,
                        mosaic=mosaic,
                        tilesize=tilesize,
                        pixel_selection_method=pixel_selection_method,
                    )

                    if data:
                        write_data_window(rio_dst=rio_tmp, data=data, window=window)

        # Convert output geotiff to COG
        copy_to_cog(
            src_path=tmpf.name,
            dst_path=output_path,
            max_overview_level=max_overview_level,
            output_profile=output_profile,
            output_profile_options=output_profile_options,
        )


def copy_to_cog(
    src_path, dst_path, max_overview_level, output_profile, output_profile_options
):
    """Copy intermediate GeoTIFF to COG
    """
    out_profile = cog_profiles.get(output_profile)
    out_profile.update({"BIGTIFF": "IF_SAFER"})
    if output_profile_options:
        out_profile.update(output_profile_options)

    config = {
        "GDAL_NUM_THREADS": "ALL_CPUS",
        "GDAL_TIFF_INTERNAL_MASK": True,
        "GDAL_TIFF_OVR_BLOCKSIZE": "128",
    }

    cog_translate(
        src_path,
        dst_path,
        out_profile,
        config=config,
        in_memory=False,
        overview_level=max_overview_level,
    )


def tile_extrema(tiles):
    """Find extrema of tiles
    """
    minx = min(tiles, key=lambda tile: tile.x).x
    miny = min(tiles, key=lambda tile: tile.y).y
    maxx = max(tiles, key=lambda tile: tile.x).x
    maxy = max(tiles, key=lambda tile: tile.y).y

    # Add one to max x and y since it's an exclusive bound
    return {"x": {"min": minx, "max": maxx + 1}, "y": {"min": miny, "max": maxy + 1}}


def read_data(
    tile: Tile,
    mosaic: MosaicJSON,
    tilesize: int,
    pixel_selection_method: MosaicMethodBase,
) -> Optional[ImageData]:
    """Read data for tile from mosaic
    """
    # Use FileBackend with no path as "fake" in-memory mosaic backend
    with FileBackend(path=None, mosaic_def=mosaic) as mosaic_backend:
        try:
            img_data, _ = mosaic_backend.tile(
                *tile, tilesize=tilesize, pixel_selection=pixel_selection_method
            )
            return img_data
        except NoAssetFoundError:
            return None


def get_random_asset(mosaic: MosaicJSON) -> str:
    """Choose random asset from mosaic definition
    """
    random_qk = random.choice(list(mosaic.tiles.keys()))
    random_asset = random.choice(mosaic.tiles[random_qk])
    return random_asset


def get_cog_profile(asset: str) -> Dict:
    """Get rasterio profile from COG
    """
    with rasterio.open(asset) as src:
        return src.profile


def write_data_window(rio_dst, data: ImageData, window: Window):
    """Write data window to rasterio source
    """
    rio_dst.write(data.data, window=window)
    rio_dst.write_mask(data.mask.astype("uint8"), window=window)


def find_window(tile: Tile, extrema: Dict, tilesize: int = 256) -> Window:
    """Find window given tile
    """
    col = tile.x - extrema["x"]["min"]
    row = tile.y - extrema["y"]["min"]
    return Window(col_off=col, row_off=row, width=tilesize, height=tilesize)


def get_output_transform(base_zoom: int, extrema: Dict, tilesize: int = 256) -> Affine:
    """Construct output transform
    """
    w, n = mercantile.xy(
        *mercantile.ul(extrema["x"]["min"], extrema["y"]["min"], base_zoom)
    )
    resolution = _meters_per_pixel(base_zoom, 0, tilesize=tilesize)
    return Affine(resolution, 0, w, 0, -resolution, n)


def get_output_profile(
    info: Dict,
    base_zoom: int,
    extrema: Dict,
    tilesize: int = 256,
    output_profile: Optional[Dict] = None,
) -> Dict:
    """Construct output profile
    """
    output_transform = get_output_transform(
        base_zoom=base_zoom, extrema=extrema, tilesize=tilesize
    )

    width = (extrema["x"]["max"] - extrema["x"]["min"]) * tilesize
    height = (extrema["y"]["max"] - extrema["y"]["min"]) * tilesize

    # TODO: add colorinterp
    params = {
        "driver": "GTiff",
        "dtype": info["dtype"],
        "count": info["count"],
        "width": width,
        "height": height,
        "crs": "epsg:3857",
        "transform": output_transform,
        "nodata": info["nodata"],
    }
    if output_profile:
        params.update(**output_profile)

    return params
