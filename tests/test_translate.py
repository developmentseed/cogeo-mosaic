"""tests cogeo_mosaic.overview."""

import json
import os

import rasterio
from click.testing import CliRunner
from rio_cogeo.cogeo import cog_validate
from rio_cogeo.profiles import cog_profiles
from rio_tiler.mercator import get_zooms

from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.translate import create_highres_cogs, create_overview_cogs

asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")
assets = [asset1, asset2]
mosaic_content = MosaicJSON.from_urls(assets).dict(exclude_none=True)

deflate_profile = cog_profiles.get("deflate")
deflate_profile.update({"blockxsize": 256, "blockysize": 256})


def test_overview_valid():
    """Should work as expected (create cogeo file)."""
    config = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "TRUE",
        "GDAL_TIFF_INTERNAL_MASK": "TRUE",
        "GDAL_TIFF_OVR_BLOCKSIZE": "128",
    }
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("mosaic.json", "w") as f:
            f.write(json.dumps(mosaic_content))

        create_overview_cogs("mosaic.json", deflate_profile, config=config, threads=1)

        assert cog_validate("mosaic_ovr_0.tif")

        with rasterio.open("mosaic_ovr_0.tif") as src:
            assert src.height == 512
            assert src.width == 512
            assert src.meta["dtype"] == "uint16"
            assert src.is_tiled
            assert src.profile["blockxsize"] == 256
            assert src.profile["blockysize"] == 256
            assert src.compression.value == "DEFLATE"
            assert src.interleaving.value == "PIXEL"
            assert src.overviews(1) == [2]

        with rasterio.open("mosaic_ovr_0.tif", OVERVIEW_LEVEL=0) as src:
            assert src.block_shapes[0] == (128, 128)


def test_highres_valid():
    """Should work as expected (create cogeo file)."""
    config = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "TRUE",
        "GDAL_TIFF_INTERNAL_MASK": "TRUE",
        "GDAL_TIFF_OVR_BLOCKSIZE": "128",
    }
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("mosaic.json", "w") as f:
            f.write(json.dumps(mosaic_content))

        create_highres_cogs(
            "mosaic.json", "mosaic_hr.tif", deflate_profile, config=config, threads=1
        )

        assert cog_validate("mosaic_hr.tif")

        with rasterio.open("mosaic_hr.tif") as src:
            assert src.height == 3072
            assert src.width == 3072
            assert src.meta["dtype"] == "uint16"
            assert src.is_tiled
            assert src.profile["blockxsize"] == 256
            assert src.profile["blockysize"] == 256
            assert src.compression.value == "DEFLATE"
            assert src.interleaving.value == "PIXEL"
            assert src.overviews(1) == [2, 4, 8, 16]
            _, maxz = get_zooms(src)
            assert maxz == mosaic_content["maxzoom"]

        with rasterio.open("mosaic_hr.tif", OVERVIEW_LEVEL=0) as src:
            assert src.block_shapes[0] == (128, 128)

        create_highres_cogs(
            "mosaic.json",
            "mosaic_hr.tif",
            deflate_profile,
            config=config,
            threads=1,
            in_memory=False,
        )

        assert cog_validate("mosaic_hr.tif")
