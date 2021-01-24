"""cogeo_mosaic.overviews: create low resolution image from a mosaic."""

import random
from tempfile import NamedTemporaryFile
from typing import Dict, Optional

import mercantile
import rasterio
from affine import Affine
from mercantile import Tile
from rasterio.windows import Window
from rio_cogeo.cogeo import cog_translate
from rio_cogeo.utils import _meters_per_pixel
from rio_tiler.models import ImageData
from supermercado.burntiles import tile_extrema

from cogeo_mosaic.backends import FileBackend
from cogeo_mosaic.errors import NoAssetFoundError
from cogeo_mosaic.mosaic import MosaicJSON


def create_overview_cog(
    mosaic: MosaicJSON, output_path: str, tilesize: int = 256, max_overview_level=None
):
    """Create overview COG from mosaic
    """
    base_zoom = mosaic.minzoom - 1
    extrema = tile_extrema(mosaic.bounds, base_zoom)

    info = get_cog_profile(get_random_asset(mosaic))
    profile = get_output_profile(
        info=info, base_zoom=base_zoom, extrema=extrema, tilesize=tilesize
    )

    with NamedTemporaryFile() as tmpf:
        with rasterio.open(tmpf.name, "w", **profile) as rio_tmp:
            # Loop over *output* tiles
            # TODO: Add progress bar
            for tile in mercantile.tiles(*mosaic.bounds, base_zoom):
                window = find_window(tile, extrema, tilesize=tilesize)
                data = read_data(tile=tile, mosaic=mosaic, tilesize=tilesize)
                if data:
                    write_data_window(rio_dst=rio_tmp, data=data, window=window)

        # Convert output geotiff to COG
        cog_translate(tmpf.name, output_path, overview_level=max_overview_level)


def read_data(tile: Tile, mosaic: MosaicJSON, tilesize: int) -> Optional[ImageData]:
    """Read data for tile from mosaic
    """
    # Use FileBackend with no path as "fake" in-memory mosaic backend
    with FileBackend(path=None, mosaic_def=mosaic) as mosaic_backend:
        try:
            img_data, _ = mosaic_backend.tile(*tile, tilesize=tilesize)
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
