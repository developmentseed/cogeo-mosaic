"""tests cogeo_mosaic.scripts.cli."""

import json
import os

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
            f.write("\n")
            f.write("\n".join(assets))
            f.write("\n")

        result = runner.invoke(cogeo_cli, ["create", "list.txt", "--quiet"])
        assert not result.exception
        assert result.exit_code == 0
        assert mosaic_content == MosaicJSON(**json.loads(result.output))

        result = runner.invoke(cogeo_cli, ["create", "list.txt", "-o", "mosaic.json"])
        assert not result.exception
        assert result.exit_code == 0
        assert mosaic_content == MosaicJSON.parse_file("mosaic.json")

        result = runner.invoke(
            cogeo_cli,
            [
                "create",
                "list.txt",
                "-o",
                "mosaic.json",
                "--name",
                "my_mosaic",
                "--description",
                "A mosaic",
                "--attribution",
                "someone",
            ],
        )
        assert not result.exception
        assert result.exit_code == 0
        mosaic = MosaicJSON.parse_file("mosaic.json")
        assert mosaic.name == "my_mosaic"
        assert mosaic.description == "A mosaic"
        assert mosaic.attribution == "someone"


def test_update_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("mosaic_1.json", "w") as f:
            f.write(json.dumps(MosaicJSON.from_urls([asset1]).dict(exclude_none=True)))

        with open("./list.txt", "w") as f:
            f.write("\n".join([asset2]))

        result = runner.invoke(
            cogeo_cli, ["update", "list.txt", "mosaic_1.json", "--quiet"]
        )
        assert not result.exception
        assert result.exit_code == 0
        with open("mosaic_1.json", "r") as f:
            updated_mosaic = json.load(f)
            updated_mosaic["version"] == "1.0.1"
            assert not mosaic_content.tiles == updated_mosaic["tiles"]

        with open("mosaic_2.json", "w") as f:
            f.write(json.dumps(MosaicJSON.from_urls([asset1]).dict(exclude_none=True)))

        result = runner.invoke(
            cogeo_cli, ["update", "list.txt", "mosaic_2.json", "--add-last", "--quiet"]
        )
        assert not result.exception
        assert result.exit_code == 0
        with open("mosaic_2.json", "r") as f:
            updated_mosaic = json.load(f)
            updated_mosaic["version"] == "1.0.1"
            assert mosaic_content.tiles == updated_mosaic["tiles"]


def test_footprint_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./list.txt", "w") as f:
            f.write("\n".join([asset1, asset2]))

        result = runner.invoke(cogeo_cli, ["footprint", "list.txt", "--quiet"])
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


def test_from_features():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("./list.txt", "w") as f:
            f.write("\n".join([asset1, asset2]))

        result = runner.invoke(
            cogeo_cli, ["footprint", "list.txt", "-o", "mosaic.geojson"]
        )
        with open("mosaic.geojson", "r") as f:
            features = f.read()

        result = runner.invoke(
            cogeo_cli,
            [
                "create-from-features",
                "--minzoom",
                "7",
                "--maxzoom",
                "9",
                "--property",
                "path",
                "--quiet",
            ],
            input=features,
        )
        assert not result.exception
        assert result.exit_code == 0
        assert mosaic_content == MosaicJSON(**json.loads(result.output))

        result = runner.invoke(
            cogeo_cli,
            [
                "create-from-features",
                "--minzoom",
                "7",
                "--maxzoom",
                "9",
                "--property",
                "path",
                "-o",
                "mosaic.json",
                "--quiet",
            ],
            input=features,
        )
        assert not result.exception
        assert result.exit_code == 0
        assert mosaic_content == MosaicJSON.parse_file("mosaic.json")

        result = runner.invoke(
            cogeo_cli,
            [
                "create-from-features",
                "--minzoom",
                "7",
                "--maxzoom",
                "9",
                "--property",
                "path",
                "--name",
                "my_mosaic",
                "--description",
                "A mosaic",
                "--attribution",
                "someone",
                "--quiet",
            ],
            input=features,
        )
        assert not result.exception
        assert result.exit_code == 0
        mosaic = MosaicJSON(**json.loads(result.output))
        assert mosaic.name == "my_mosaic"
        assert mosaic.description == "A mosaic"
        assert mosaic.attribution == "someone"


def test_info_valid():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
        result = runner.invoke(cogeo_cli, ["info", mosaic, "--json"])
        assert not result.exception
        assert result.exit_code == 0
        info = json.loads(result.output)
        assert info["Backend"] == "File"
        assert not info["Compressed"]

        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
        result = runner.invoke(cogeo_cli, ["info", mosaic, "--json"])
        assert not result.exception
        assert result.exit_code == 0
        info = json.loads(result.output)
        assert info["Backend"] == "File"
        assert info["Compressed"]

        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json.gz")
        result = runner.invoke(cogeo_cli, ["info", mosaic])
        assert not result.exception
        assert result.exit_code == 0
        assert "Compressed: True" in result.output


def test_to_geojson():
    """Should work as expected."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
        result = runner.invoke(cogeo_cli, ["to-geojson", mosaic])
        assert not result.exception
        assert result.exit_code == 0
        info = result.output.split("\n")
        assert len(info) == 10
        assert json.loads(info[0])["properties"]["nb_assets"] == 1

        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
        result = runner.invoke(cogeo_cli, ["to-geojson", mosaic, "--features"])
        assert not result.exception
        assert result.exit_code == 0
        info = result.output.split("\n")
        assert len(info) == 10
        assert json.loads(info[0])["properties"]["nb_assets"] == 1

        mosaic = os.path.join(os.path.dirname(__file__), "fixtures", "mosaic.json")
        result = runner.invoke(cogeo_cli, ["to-geojson", mosaic, "--collect"])
        assert not result.exception
        assert result.exit_code == 0
        info = json.loads(result.output)
        assert len(info["features"]) == 9
