"""test cogeo_mosaic.supermorecado submodule.

Note: most of the test are adapted from https://github.com/mapbox/supermercado/blob/main/tests/test_cli.py
"""

import planetcantile

from cogeo_mosaic.supermorecado import burnTiles

MARS_EQUI_CLON_0 = planetcantile.planetary_tms.get('IAU_2015_49910')

def test_burn_tile_center_point_roundtrip():
    tile = [500000, 250000, 19]
    print(planetcantile.__file__)
    w, s, e, n = MARS_EQUI_CLON_0.bounds(*tile)

    x = (e - w) / 2 + w
    y = (n - s) / 2 + s
    point_feature = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "Point", "coordinates": [x, y]},
    }
    assert burnTiles(tms=MARS_EQUI_CLON_0).burn([point_feature], 19).tolist() == [tile]


def test_burn_tile_center_lines_roundtrip():
    tiles = list(MARS_EQUI_CLON_0.children([0, 0, 0]))
    bounds = (MARS_EQUI_CLON_0.bounds(*t) for t in tiles)
    coords = (((e - w) / 2 + w, (n - s) / 2 + s) for w, s, e, n in bounds)

    features = {
        "type": "Feature",
        "properties": {},
        "geometry": {"type": "LineString", "coordinates": list(coords)},
    }

    output_tiles = burnTiles(tms=MARS_EQUI_CLON_0).burn([features], 1).tolist()
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
    assert burnTiles(tms=MARS_EQUI_CLON_0).burn([tilegeom], 13).tolist() == [[2618, 2376, 13], [2619, 2376, 13], [2618, 2377, 13], [2619, 2377, 13]]
