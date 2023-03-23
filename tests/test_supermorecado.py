"""test cogeo_mosaic.supermorecado submodule.

Note: most of the test are adapted from https://github.com/mapbox/supermercado/blob/main/tests/test_cli.py
"""

import morecantile

from cogeo_mosaic.supermorecado import burnTiles

WEB_MERCATOR_TMS = morecantile.tms.get("WebMercatorQuad")


def test_burn_tile_center_point_roundtrip():
    tile = [83885, 202615, 19]
    w, s, e, n = WEB_MERCATOR_TMS.bounds(*tile)

    x = (e - w) / 2 + w
    y = (n - s) / 2 + s

    point_feature = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [x, y]},
    }

    assert burnTiles().burn([point_feature], 19).tolist() == [tile]


def test_burn_tile_center_lines_roundtrip():
    tiles = list(WEB_MERCATOR_TMS.children([0, 0, 0]))
    bounds = (WEB_MERCATOR_TMS.bounds(*t) for t in tiles)
    coords = (((e - w) / 2 + w, (n - s) / 2 + s) for w, s, e, n in bounds)

    features = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "LineString", "coordinates": list(coords)},
    }

    output_tiles = burnTiles().burn([features], 1).tolist()
    assert sorted(output_tiles) == sorted([list(t) for t in tiles])


def test_burn_cli_tile_shape():
    tilegeom = {
        "bbox": [-122.4755859375, 37.75334401310657, -122.431640625, 37.78808138412046],
        "geometry": {
            "coordinates": [
                [
                    [-122.4755859375, 37.75334401310657],
                    [-122.4755859375, 37.78808138412046],
                    [-122.431640625, 37.78808138412046],
                    [-122.431640625, 37.75334401310657],
                    [-122.4755859375, 37.75334401310657],
                ]
            ],
            "type": "Polygon",
        },
        "id": "(1309, 3166, 13)",
        "properties": {"title": "XYZ tile (1309, 3166, 13)"},
        "type": "Feature",
    }
    assert burnTiles().burn([tilegeom], 13).tolist() == [[1309, 3166, 13]]

    tilegeom = {
        "bbox": [-122.4755859375, 37.75334401310657, -122.431640625, 37.78808138412046],
        "geometry": {
            "coordinates": [
                [
                    [
                        [-122.4755859375, 37.75334401310657],
                        [-122.4755859375, 37.78808138412046],
                        [-122.431640625, 37.78808138412046],
                        [-122.431640625, 37.75334401310657],
                        [-122.4755859375, 37.75334401310657],
                    ]
                ]
            ],
            "type": "MultiPolygon",
        },
        "id": "(1309, 3166, 13)",
        "properties": {"title": "XYZ tile (1309, 3166, 13)"},
        "type": "Feature",
    }
    assert burnTiles().burn([tilegeom], 13).tolist() == [[1309, 3166, 13]]
