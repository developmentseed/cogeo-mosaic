import json
import os
import warnings

import morecantile
import pyproj
import pytest

from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.errors import MultipleDataTypeError
from cogeo_mosaic.mosaic import MosaicJSON, default_filter

tms_3857 = morecantile.tms.get("WebMercatorQuad")
tms_4326 = morecantile.tms.get("WorldCRS84Quad")
tms_5041 = morecantile.tms.get("UPSArcticWGS84Quad")
tms_4087 = morecantile.TileMatrixSet.custom(
    [-20037508.34, -10018754.17, 20037508.34, 10018754.17],
    pyproj.CRS("EPSG:4087"),
    id="WGS84WorldEquidistantCylindrical",
)

basepath = os.path.join(os.path.dirname(__file__), "fixtures")
mosaic_gz = os.path.join(basepath, "mosaic.json.gz")
mosaic_json = os.path.join(basepath, "mosaic.json")
asset1 = os.path.join(basepath, "cog1.tif")
asset2 = os.path.join(basepath, "cog2.tif")

asset1_uint32 = os.path.join(basepath, "cog1_uint32.tif")
asset1_small = os.path.join(basepath, "cog1_small.tif")

mars_ctx_asset = os.path.join(basepath, "mars_ctx_stac_asset.json")

with open(mosaic_json, "r") as f:
    mosaic_content = json.loads(f.read())
    for qk, asset in mosaic_content["tiles"].items():
        mosaic_content["tiles"][qk] = [os.path.join(basepath, item) for item in asset]


def _filter_and_sort(*args, **kwargs):
    dataset = default_filter(*args, **kwargs)
    return sorted(dataset, key=lambda x: x["properties"]["path"], reverse=True)


def test_mosaic_create():
    """Fetch info from dataset and create the mosaicJSON definition."""
    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets, quiet=True)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert mosaic.tiles == mosaic_content["tiles"]
    assert not mosaic.tilematrixset

    mosaic = MosaicJSON.from_urls(
        assets, tilematrixset=morecantile.tms.get("WebMercatorQuad"), quiet=True
    )
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert mosaic.tiles == mosaic_content["tiles"]
    assert mosaic.tilematrixset.id == "WebMercatorQuad"

    mosaic = MosaicJSON.from_urls(assets, minzoom=7, maxzoom=9)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]
    assert mosaic.minzoom == mosaic_content["minzoom"]
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    mosaic = MosaicJSON.from_urls(assets, minzoom=7, maxzoom=9, tilematrixset=tms_3857)
    assert mosaic.tilematrixset.id == "WebMercatorQuad"

    # 5% tile cover filter
    mosaic = MosaicJSON.from_urls(assets, minimum_tile_cover=0.059)
    assert not list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())

    # sort by tile cover
    mosaic = MosaicJSON.from_urls(assets, tile_cover_sort=True)
    assert list(mosaic.tiles.keys()) == list(mosaic_content["tiles"].keys())
    assert not mosaic.tiles == mosaic_content["tiles"]

    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets)
    assert [round(b, 3) for b in list(mosaic.bounds)] == [
        round(b, 3) for b in mosaic_content["bounds"]
    ]
    assert mosaic.maxzoom == mosaic_content["maxzoom"]

    # Make sure no warning is emmited
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        MosaicJSON.from_urls([asset1_small, asset2], minzoom=7, maxzoom=9)

    # Multiple MaxZoom
    with pytest.warns(UserWarning):
        assets = [asset1_small, asset2]
        MosaicJSON.from_urls(assets)

    # Mixed datatype
    with pytest.raises(MultipleDataTypeError):
        assets = [asset1_uint32, asset2]
        MosaicJSON.from_urls(assets)

    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets, asset_filter=_filter_and_sort, quiet=True)
    assert not mosaic.tiles == mosaic_content["tiles"]


def test_mosaic_create_tms():
    """Create mosaic with TMS"""
    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(assets, quiet=True, tilematrixset=tms_3857)
    assert mosaic.tilematrixset.id == "WebMercatorQuad"

    # using non Quadkey TMS
    with pytest.raises(AssertionError):
        mosaic = MosaicJSON.from_urls(assets, tilematrixset=tms_4326, quiet=True)

    # Test a Quad (1:1) polar projection
    mosaic = MosaicJSON.from_urls(assets, tilematrixset=tms_5041, quiet=True)
    assert len(mosaic.tiles) == 6
    assert mosaic.tilematrixset.id == "UPSArcticWGS84Quad"

    # Test a Earth Equirectangular projection, currently improperly using quadtree indexing
    mosaic = MosaicJSON.from_urls(assets, tilematrixset=tms_4087, quiet=True)
    assert len(mosaic.tiles) == 6
    assert mosaic.tilematrixset.id == "WGS84WorldEquidistantCylindrical"


def test_mosaic_create_additional_metadata():
    """add metadata info to"""
    assets = [asset1, asset2]
    mosaic = MosaicJSON.from_urls(
        assets,
        quiet=True,
        tilematrixset=tms_3857,
        asset_type="COG",
        asset_prefix=basepath,
        data_type="uint16",
        layers={
            "true-color": {
                "bidx": [1, 2, 3],
                "rescale": [(0, 1000), (0, 1100), (0, 3000)],
            }
        },
    )
    assert mosaic.asset_type == "COG"
    assert mosaic.asset_prefix == basepath
    assert mosaic.data_type == "uint16"
    assert mosaic.layers["true-color"]
    assert mosaic.tiles["0302301"] == ["/cog1.tif", "/cog2.tif"]


@pytest.mark.skipif(
    tuple(map(int, pyproj.__version__.split("."))) < (3, 6, 0),
    reason="requires proj >= 9.2.1",
)
def test_mars_mosaic_create():
    # first define the tilematrixset manually
    MARS2000_SPHERE = pyproj.CRS.from_user_input("IAU_2015:49900")
    MARS_MERCATOR = pyproj.CRS.from_user_input("IAU_2015:49990")
    # same boundaries as Earth mercator
    mars_tms = morecantile.TileMatrixSet.custom(
        [
            -179.9999999999996,
            -85.05112877980656,
            179.9999999999996,
            85.05112877980656,
        ],
        MARS_MERCATOR,
        extent_crs=MARS2000_SPHERE,
        title="Web Mercator Mars",
    )
    # load the mars_ctx_stac_assset.json file
    with open(mars_ctx_asset, "r") as f:
        stac_asset = json.load(f)
    # these stac item has multiple assets so grab the DTM
    stac_asset["properties"]["path"] = stac_asset["assets"]["dtm"]["href"]
    # now construct the mosaicjson object
    mosaic_json = MosaicJSON.from_features(
        [
            stac_asset,
        ],
        minzoom=7,
        maxzoom=30,
        tilematrixset=mars_tms,
    )
    assert mosaic_json is not None
    assert mosaic_json.tilematrixset == mars_tms
    assert len(mosaic_json.tiles) > 0
    # now test the mosaic backend
    with MosaicBackend("mosaic.json", mosaic_def=mosaic_json, tms=mars_tms) as mosaic:
        assert isinstance(mosaic, FileBackend)
        assert mosaic.tms == mars_tms
        assert mosaic.crs == mars_tms.rasterio_geographic_crs
        assert len(mosaic.assets_for_point(77.28, 18, mars_tms.geographic_crs)) > 0
        assert (
            len(mosaic.assets_for_bbox(77.2, 17.5, 77.4, 18.5, mars_tms.geographic_crs))
            > 0
        )
        assert (
            len(mosaic.assets_for_point(77.28, 18, mars_tms.rasterio_geographic_crs)) > 0
        )
        assert (
            len(
                mosaic.assets_for_bbox(
                    77.2, 17.5, 77.4, 18.5, mars_tms.rasterio_geographic_crs
                )
            )
            > 0
        )
        assert len(mosaic.assets_for_point(77.25, 18.0)) > 0
        assert len(mosaic.assets_for_bbox(77.2, 17.5, 77.4, 18.5)) > 0
