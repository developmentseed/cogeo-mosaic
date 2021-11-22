"""cogeo-mosaic In-Memory backend."""

from typing import Dict, Type, Union

import attr
from rasterio.crs import CRS
from rio_tiler.constants import WGS84_CRS
from rio_tiler.io import BaseReader, COGReader, MultiBandReader, MultiBaseReader

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

    reader: Union[
        Type[BaseReader],
        Type[MultiBaseReader],
        Type[MultiBandReader],
    ] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    # We put `input` outside the init method
    input: str = attr.ib(init=False, default=":memory:")

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
