"""Supermercado.burntiles but for other TMS."""

from typing import Dict, List, Tuple
import attr

import numpy as np
import morecantile
from affine import Affine

from rasterio import features
from rio_tiler.constants import WEB_MERCATOR_TMS


@attr.s
class burntiles:

    tms: morecantile.TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)

    ## TODO Add check for quadkey support

    def project_geom(self, geom: Dict) -> Dict:
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

    def _feature_extrema(self, geometry: Dict) -> Tuple[float, float, float, float]:
        if geometry["type"] == "Polygon":
            x, y = zip(*[c for part in geometry["coordinates"] for c in part])

        elif geometry["type"] == "LineString":
            x, y = zip(*[c for c in geometry["coordinates"]])

        elif geometry["type"] == "Point":
            x, y = geometry["coordinates"]
            return x, y, x, y

        return min(x), min(y), max(x), max(y)

    def find_extrema(self, features: List[Dict]) -> Tuple[float, float, float, float]:
        epsilon = 1.0e-10
        min_x, min_y, max_x, max_y = zip(
            *[self._feature_extrema(f["geometry"]) for f in features]
        )

        return (
            min(min_x) + epsilon,
            max(min(min_y) + epsilon, -85.0511287798066),
            max(max_x) - epsilon,
            min(max(max_y) - epsilon, 85.0511287798066),
        )


    def tile_extrema(self, bounds, zoom):
        minimumTile = self.tms.tile(bounds[0], bounds[3], zoom)
        maximumTile = self.tms.tile(bounds[2], bounds[1], zoom)

        return {
            "x": {"min": minimumTile.x, "max": maximumTile.x + 1},
            "y": {"min": minimumTile.y, "max": maximumTile.y + 1},
        }


    def make_transform(self, tilerange: Dict, zoom: int) -> Affine:

        ulx, uly = self.tms.xy(
            *self.tms.ul(tilerange["x"]["min"], tilerange["y"]["min"], zoom)
        )

        lrx, lry = self.tms.xy(
            *self.tms.ul(tilerange["x"]["max"], tilerange["y"]["max"], zoom)
        )

        xcell = (lrx - ulx) / float(tilerange["x"]["max"] - tilerange["x"]["min"])
        ycell = (uly - lry) / float(tilerange["y"]["max"] - tilerange["y"]["min"])

        return Affine(xcell, 0, ulx, 0, -ycell, uly)


    def burn(self, polys: List[Dict], zoom: int):
        bounds = self.find_extrema(polys)

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

        xys = np.fliplr(np.dstack(np.where(burn))[0])

        xys[:, 0] += tilerange["x"]["min"]
        xys[:, 1] += tilerange["y"]["min"]

        return np.append(xys, np.zeros((xys.shape[0], 1), dtype=np.uint8) + zoom, axis=1)
