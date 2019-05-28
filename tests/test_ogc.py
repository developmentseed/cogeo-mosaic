"""tests cogeo_mosaic.ogc."""

from click.testing import CliRunner

import rasterio
from cogeo_mosaic import ogc


def test_fill_template():
    """Create a valid wmts template."""
    runner = CliRunner()
    with runner.isolated_filesystem():
        xml = ogc.wmts_template("http://myendpoint.com", "my_mosaic_layer")
        with open("wmts.xml", "w") as f:
            f.write(xml)
        with rasterio.open("wmts.xml") as src_dst:
            meta = src_dst.meta
            ovr = src_dst.overviews(1)
            assert meta["driver"] == "WMTS"
            assert meta["width"] == 1073741824
            assert meta["height"] == 1073741824
            assert meta["crs"].to_dict() == {"init": "epsg:3857"}
            assert list(src_dst.bounds) == [
                -20037508.34278925,
                -20037508.342789393,
                20037508.342789393,
                20037508.34278925,
            ]
            assert ovr
            tags = src_dst.tags()
            assert tags["ABSTRACT"] == "cogeo-mosaic"
            assert tags["TITLE"] == "Cloud Optimizied GeoTIFF Mosaic"

        xml = ogc.wmts_template(
            "http://myendpoint.com",
            "my_mosaic_layer",
            query_string="rescale=-1,1",
            minzoom=6,
            maxzoom=12,
            bounds=[-10, 10, 10, -10],
            tile_scale=2,
            tile_format="jpeg",
            title="my cog mosaic",
        )
        with open("wmts.xml", "w") as f:
            f.write(xml)
        with rasterio.open("wmts.xml") as src_dst:
            meta = src_dst.meta
            ovr = src_dst.overviews(1)
            assert meta["driver"] == "WMTS"
            assert meta["width"] == 116509
            assert meta["height"] == 117105
            assert meta["crs"].to_dict() == {"init": "epsg:3857"}
            assert list(src_dst.bounds) == [
                -1113209.7706881687,
                -1118885.2200384848,
                1113190.66143124,
                1118904.3292954154,
            ]
            assert len(ovr) == 6
            tags = src_dst.tags()
            assert tags["TITLE"] == "my cog mosaic"
