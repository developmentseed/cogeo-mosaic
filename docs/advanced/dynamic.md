
The mosaic backend abstract `BaseBackend` has been designed to be really flexible and compatible with dynamic tiler built for rio-tiler `BaseReader`. It also enables the creation of `dynamic` mosaic where NO mosaicJSON document really exists.

The `BaseBackend` ABC class defines that the sub class should:

- have a `mosaic_def` object (MosaicJSON) or a path as input
- have `_read`, `write` and `update` methods defined

Other attributes can default to the BaseBackend defaults:

- `tms` is set to WebMercator
- `minzoom` is set to `0` (mosaicJSON default)
- `maxzoom` is set to `30` (mosaicJSON default)
- `bounds` is set to `(-180, -90, 180, 90)`  (mosaicJSON default)

all other methods are built on top of the MosaicJSON definition.

For a `dynamic` backend we do not want to construct nor store a mosaicJSON object but fetch the `assets` needed
on each `tile()` or `point()` request.

For this to be possible we need to :

- create a `fake` empty mosaicJSON
- create passthrough `_read`, `write` and `update` methods
- create custom `get_assets()`, `assets_for_tile()` and `assets_for_point()` methods.

Here is an example of a `Dynamic` STAC backend where on each `tile()` or `point()` call, the backend will send a request to the STAC api endpoint to find the assets interesecting with the request.

```python
from typing import Dict, Tuple, Type, Optional, List

import attr
from morecantile import TileMatrixSet
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.io import BaseReader
from rio_tiler.io import STACReader

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.stac import _fetch, default_stac_accessor
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class DynamicStacBackend(BaseBackend):
    """Like a STAC backend but dynamic"""

    # input should be the STAC-API url
    input: str = attr.ib()

    # Addition required attribute (STAC Query)
    query: Dict = attr.ib(factory=dict)

    minzoom: int = attr.ib(default=None)
    maxzoom: int = attr.ib(default=None)

    reader: Type[BaseReader] = attr.ib(default=STACReader)
    reader_options: Dict = attr.ib(factory=dict)

    # STAC API related options
    # max_items |  next_link_key | limit
    stac_api_options: Dict = attr.ib(factory=dict)

    # The reader is read-only, we can't pass mosaic_def to the init method
    mosaic_def: MosaicJSON = attr.ib(init=False)

    _backend_name = "DynamicSTAC"

    def __attrs_post_init__(self):
        """Post Init."""
        # Construct a FAKE/Empty mosaicJSON
        # mosaic_def has to be defined. As we do for the DynamoDB and SQLite backend
        self.mosaic_def = MosaicJSON(
            mosaicjson="0.0.2",
            name="it's fake but it's ok",
            minzoom=self.minzoom or self.tms.minzoom,
            maxzoom=self.maxzoom or self.tms.maxzoom,
            tiles=[]  # we set `tiles` to an empty list.
        )

    def write(self, overwrite: bool = True):
        """This method is not used but is required by the abstract class."""
        pass

    def update(self):
        """We overwrite the default method."""
        pass

    def _read(self) -> MosaicJSON:
        """This method is not used but is required by the abstract class."""
        pass

    def assets_for_tile(self, x: int, y: int, z: int) -> List[str]:
        """Retrieve assets for tile."""
        bounds = self.tms.bounds(x, y, z)
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [bounds[0], bounds[3]],
                    [bounds[0], bounds[1]],
                    [bounds[2], bounds[1]],
                    [bounds[2], bounds[3]],
                    [bounds[0], bounds[3]],
                ]
            ],
        }
        return self.get_assets(geom)

    def assets_for_point(self, lng: float, lat: float) -> List[str]:
        """Retrieve assets for point.

        Note: some API only accept Polygon.
        """
        EPSILON = 1e-14
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [lng - EPSILON, lat + EPSILON],
                    [lng - EPSILON, lat - EPSILON],
                    [lng + EPSILON, lat - EPSILON],
                    [lng + EPSILON, lat + EPSILON],
                    [lng - EPSILON, lat + EPSILON],
                ]
            ],
        }
        return self.get_assets(geom)

    def get_assets(self, geom) -> List[str]:
        """Send query to the STAC-API and retrieve assets."""
        query = self.query.copy()
        query["intersects"] = geom

        features = _fetch(
            self.input,
            query,
            **self.stac_api_options,
        )
        return [default_stac_accessor(f) for f in features]

    @property
    def _quadkeys(self) -> List[str]:
        return []
```

Full examples can be found at [examples/Create_a_Dynamic_StacBackend/](https://developmentseed.org/cogeo-mosaic/examples/Create_a_Dynamic_StacBackend/) and [examples/Create_a_Dynamic_RtreeBackend/](https://developmentseed.org/cogeo-mosaic/examples/Create_a_Dynamic_RtreeBackend/).
