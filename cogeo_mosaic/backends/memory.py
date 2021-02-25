"""cogeo-mosaic In-Memory backend."""

from typing import Dict, Tuple, Type

import attr
from morecantile import TileMatrixSet
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.io import BaseReader, COGReader

from cogeo_mosaic.backends.base import BaseBackend, _convert_to_mosaicjson
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class MemoryBackend(BaseBackend):
    """InMemory Backend Adapter

    Examples:
        >>> with MemoryBackend(mosaicJSON) as mosaic:
                mosaic.tile(0, 0, 0)
    """

    mosaic_def: MosaicJSON = attr.ib(converter=_convert_to_mosaicjson)
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    # TMS is outside the init because mosaicJSON and cogeo-mosaic only
    # works with WebMercator (mercantile) for now.
    tms: TileMatrixSet = attr.ib(init=False, default=WEB_MERCATOR_TMS)

    # default values for bounds and zoom
    bounds: Tuple[float, float, float, float] = attr.ib(
        init=False, default=(-180, -90, 180, 90)
    )
    minzoom: int = attr.ib(init=False, default=0)
    maxzoom: int = attr.ib(init=False, default=30)

    path: str = attr.ib(init=False, default=":memory:")

    _backend_name = "MEM"

    def __attrs_post_init__(self):
        """Post Init."""
        self.minzoom = self.mosaic_def.minzoom
        self.maxzoom = self.mosaic_def.maxzoom
        self.bounds = self.mosaic_def.bounds

    def write(self, overwrite: bool = True):
        """Write mosaicjson document."""
        pass

    def _read(self) -> MosaicJSON:
        pass
