"""tests cogeo_mosaic.overview."""

import json
import os

import rasterio
from click.testing import CliRunner
from rio_cogeo.cogeo import cog_validate
from rio_cogeo.profiles import cog_profiles

from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.overviews import create_overview_cogs

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
            assert src.height == 256
            assert src.width == 256
            assert src.meta["dtype"] == "uint16"
            assert src.is_tiled
            assert src.profile["blockxsize"] == 256
            assert src.profile["blockysize"] == 256
            assert src.compression.value == "DEFLATE"
            assert src.interleaving.value == "PIXEL"
            assert src.overviews(1) == []
