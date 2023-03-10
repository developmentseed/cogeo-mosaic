"""Supermercado.burntiles but for other TMS.

This submodule is adapted from mapbox/supermercado project:

The MIT License (MIT)

Copyright (c) 2015 Mapbox

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

from typing import Any, Dict, Sequence, Tuple

import attr
import morecantile
import numpy
from affine import Affine
from rasterio import features

WEB_MERCATOR_TMS = morecantile.tms.get("WebMercatorQuad")


def _feature_extrema(geometry: Dict) -> Tuple[float, float, float, float]:
    """Get bounds extrema for a feature."""
    if geometry["type"] == "Polygon":
        x, y = zip(*[c for part in geometry["coordinates"] for c in part])

    elif geometry["type"] == "MultiPolygon":
        x, y = zip(
            *[c for poly in geometry["coordinates"] for part in poly for c in part]
        )

    elif geometry["type"] == "LineString":
        x, y = zip(*[c for c in geometry["coordinates"]])

    elif geometry["type"] == "Point":
        x, y = geometry["coordinates"]
        return x, y, x, y

    return min(x), min(y), max(x), max(y)


def find_extrema(
    features: Sequence[Dict[Any, Any]]
) -> Tuple[float, float, float, float]:
    """Get bounds extrema for a set of features."""
    epsilon = 1.0e-10
    min_x, min_y, max_x, max_y = zip(
        *[_feature_extrema(f["geometry"]) for f in features]
    )

    return (
        min(min_x) + epsilon,
        max(min(min_y) + epsilon, -85.0511287798066),
        max(max_x) - epsilon,
        min(max(max_y) - epsilon, 85.0511287798066),
    )


@attr.s
class burnTiles:
    """Burntiles."""

    tms: morecantile.TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    @tms.validator
    def _check_for_quadtree_support(self, attribute, value: morecantile.TileMatrixSet):
        if not value._is_quadtree:
            raise ValueError(f"{value.identifier} TMS does not support quadtree.")

    def project_geom(self, geom: Dict) -> Dict:
        """reproject geom in TMS CRS."""
        if geom["type"] == "Polygon":
            return {
                "type": geom["type"],
                "coordinates": [
                    [self.tms.xy(*coords) for coords in part]
                    for part in geom["coordinates"]
                ],
            }

        elif geom["type"] == "LineString":
            return {
                "type": geom["type"],
                "coordinates": [self.tms.xy(*coords) for coords in geom["coordinates"]],
            }

        elif geom["type"] == "Point":
            return {
                "type": geom["type"],
                "coordinates": self.tms.xy(*geom["coordinates"]),
            }

        elif geom["type"] == "MultiPolygon":
            return {
                "type": geom["type"],
                "coordinates": [
                    [[self.tms.xy(*coords) for coords in part] for part in poly]
                    for poly in geom["coordinates"]
                ],
            }

        else:
            raise Exception(f"Invalid geometry type {geom['type']}")

    def tile_extrema(self, bounds, zoom):
        """Tiles min/max at the given zoom for bounds."""
        minimumTile = self.tms.tile(bounds[0], bounds[3], zoom)
        maximumTile = self.tms.tile(bounds[2], bounds[1], zoom)

        return {
            "x": {"min": minimumTile.x, "max": maximumTile.x + 1},
            "y": {"min": minimumTile.y, "max": maximumTile.y + 1},
        }

    def make_transform(self, tilerange: Dict, zoom: int) -> Affine:
        """Create Affine Transform from extrema."""
        ulx, uly = self.tms.xy(
            *self.tms.ul(tilerange["x"]["min"], tilerange["y"]["min"], zoom)
        )

        lrx, lry = self.tms.xy(
            *self.tms.ul(tilerange["x"]["max"], tilerange["y"]["max"], zoom)
        )

        xcell = (lrx - ulx) / float(tilerange["x"]["max"] - tilerange["x"]["min"])
        ycell = (uly - lry) / float(tilerange["y"]["max"] - tilerange["y"]["min"])

        return Affine(xcell, 0, ulx, 0, -ycell, uly)

    def burn(self, polys: Sequence[Dict[Any, Any]], zoom: int) -> numpy.ndarray:
        """Burn geometries to Tiles."""
        bounds = find_extrema(polys)

        tilerange = self.tile_extrema(bounds, zoom)
        afftrans = self.make_transform(tilerange, zoom)

        burn = features.rasterize(
            ((self.project_geom(geom["geometry"]), 255) for geom in polys),
            out_shape=(
                (
                    tilerange["y"]["max"] - tilerange["y"]["min"],
                    tilerange["x"]["max"] - tilerange["x"]["min"],
                )
            ),
            transform=afftrans,
            all_touched=True,
        )

        xys = numpy.fliplr(numpy.dstack(numpy.where(burn))[0])
        xys[:, 0] += tilerange["x"]["min"]
        xys[:, 1] += tilerange["y"]["min"]

        return numpy.append(
            xys, numpy.zeros((xys.shape[0], 1), dtype=numpy.uint8) + zoom, axis=1
        )
