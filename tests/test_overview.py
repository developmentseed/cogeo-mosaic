"""tests cogeo_mosaic.overview."""

import os

import pytest
import rasterio
from click.testing import CliRunner
from rio_cogeo.profiles import cog_profiles

from cogeo_mosaic.create import create_mosaic
from cogeo_mosaic.overviews import create_low_level_cogs

asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")
assets = [asset1, asset2]
mosaic_content = create_mosaic(assets)

deflate_profile = cog_profiles.get("deflate")
deflate_profile.update({"blockxsize": 256, "blockysize": 256})


@pytest.fixture(autouse=True)
def testing_env_var(monkeypatch):
    """Set GDAL env."""
    monkeypatch.setenv("GDAL_DISABLE_READDIR_ON_OPEN", "TRUE")
    monkeypatch.setenv("GDAL_TIFF_INTERNAL_MASK", "TRUE")
    monkeypatch.setenv("GDAL_TIFF_OVR_BLOCKSIZE", "128")


def test_overview_valid():
    """Should work as expected (create cogeo file)."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        create_low_level_cogs(mosaic_content, deflate_profile)
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
            assert src.tags()["OVR_RESAMPLING_ALG"] == "NEAREST"

        with rasterio.open("mosaic_ovr_0.tif", OVERVIEW_LEVEL=0) as src:
            assert src.block_shapes[0] == (128, 128)
