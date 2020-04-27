"""tests cogeo_mosaic.scripts.cli."""

import json
import os

import rasterio
from click.testing import CliRunner

from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.scripts.cli import cogeo_cli

asset1 = os.path.join(os.path.dirname(__file__), "fixtures", "cog1.tif")
asset2 = os.path.join(os.path.dirname(__file__), "fixtures", "cog2.tif")
assets = [asset1, asset2]
mosaic_content = MosaicJSON.from_urls(assets)


def test_create_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./list.txt", "w") as f:
            f.write("\n".join(assets))

        result = runner.invoke(cogeo_cli, ["create", "list.txt", "--quiet"])
        assert not result.exception
        assert result.exit_code == 0
        assert mosaic_content == MosaicJSON(**json.loads(result.output))

        result = runner.invoke(cogeo_cli, ["create", "list.txt", "-o", "mosaic.json"])
        assert not result.exception
        assert result.exit_code == 0
        with open("mosaic.json", "r") as f:
            assert mosaic_content == MosaicJSON(**json.load(f))


def test_update_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("mosaic.json", "w") as f:
            f.write(json.dumps(MosaicJSON.from_urls([asset1]).dict(exclude_none=True)))

        with open("./list.txt", "w") as f:
            f.write("\n".join([asset2]))

        result = runner.invoke(cogeo_cli, ["update", "list.txt", "mosaic.json"])
        assert not result.exception
        assert result.exit_code == 0
        updated_mosaic = json.loads(result.output)
        updated_mosaic["version"] == "1.0.1"
        assert not mosaic_content.tiles == updated_mosaic["tiles"]

        result = runner.invoke(
            cogeo_cli, ["update", "list.txt", "mosaic.json", "--on-bottom"]
        )
        assert not result.exception
        assert result.exit_code == 0
        updated_mosaic = json.loads(result.output)
        updated_mosaic["version"] == "1.0.1"
        assert mosaic_content.tiles == updated_mosaic["tiles"]

        result = runner.invoke(
            cogeo_cli,
            ["update", "list.txt", "mosaic.json", "--overwrite", "--on-bottom"],
        )
        assert not result.exception
        assert result.exit_code == 0
        with open("mosaic.json", "r") as f:
            updated_mosaic = json.load(f)
            updated_mosaic["version"] == "1.0.1"
            assert mosaic_content.tiles == updated_mosaic["tiles"]


def test_footprint_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./list.txt", "w") as f:
            f.write("\n".join([asset1, asset2]))

        result = runner.invoke(cogeo_cli, ["footprint", "list.txt"])
        assert not result.exception
        assert result.exit_code == 0
        footprint = json.loads(result.output)
        assert len(footprint["features"]) == 2

        result = runner.invoke(
            cogeo_cli, ["footprint", "list.txt", "-o", "mosaic.geojson"]
        )
        assert not result.exception
        assert result.exit_code == 0
        with open("mosaic.geojson", "r") as f:
            footprint = json.load(f)
            assert len(footprint["features"]) == 2


def test_overview_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("mosaic.json", "w") as f:
            f.write(json.dumps(mosaic_content.dict(exclude_none=True)))

        result = runner.invoke(cogeo_cli, ["overview", "mosaic.json"])
        assert not result.exception
        assert result.exit_code == 0
        with rasterio.open("mosaic_0.tif") as src_dst:
            assert src_dst.width == 512
            assert src_dst.height == 512
            assert not src_dst.overviews(1)
            assert src_dst.compression.value == "DEFLATE"

        result = runner.invoke(
            cogeo_cli,
            [
                "overview",
                "mosaic.json",
                "--prefix",
                "ovr",
                "--cog-profile",
                "raw",
                "--co",
                "BLOCKXSIZE=128",
                "--co",
                "BLOCKYSIZE=128",
            ],
        )
        assert not result.exception
        assert result.exit_code == 0
        with rasterio.open("ovr_0.tif") as src_dst:
            assert src_dst.width == 512
            assert src_dst.height == 512
            assert src_dst.overviews(1) == [2, 4]
            assert not src_dst.compression
