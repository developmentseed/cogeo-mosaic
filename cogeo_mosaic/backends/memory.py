"""cogeo-mosaic In-Memory backend."""

from typing import Dict, Type, Union

import attr
from morecantile import TileMatrixSet
from rasterio.crs import CRS
from rio_tiler.constants import WEB_MERCATOR_TMS, WGS84_CRS
from rio_tiler.io import BaseReader, MultiBandReader, MultiBaseReader, Reader

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

    tms: TileMatrixSet = attr.ib(default=WEB_MERCATOR_TMS)
    minzoom: int = attr.ib(default=None)
    maxzoom: int = attr.ib(default=None)

    reader: Union[
        Type[BaseReader],
        Type[MultiBaseReader],
        Type[MultiBandReader],
    ] = attr.ib(default=Reader)
    reader_options: Dict = attr.ib(factory=dict)

    geographic_crs: CRS = attr.ib(default=WGS84_CRS)

    # We put `input` outside the init method
    input: str = attr.ib(init=False, default=":memory:")

    _backend_name = "MEM"

    def __attrs_post_init__(self):
        """Post Init."""
        self.bounds = self.mosaic_def.bounds

        mosaic_tms = self.mosaic_def.tilematrixset or WEB_MERCATOR_TMS
        if mosaic_tms == self.tms:
            self.minzoom = (
                self.minzoom if self.minzoom is not None else self.mosaic_def.minzoom
            )
            self.maxzoom = (
                self.maxzoom if self.maxzoom is not None else self.mosaic_def.maxzoom
            )

    def write(self, overwrite: bool = True):
        """Write mosaicjson document."""
        pass

    def _read(self) -> MosaicJSON:
        pass
