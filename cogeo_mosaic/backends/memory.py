"""cogeo-mosaic InMemory backend."""

from typing import Dict, List, Tuple, Type

import attr
from morecantile import TileMatrixSet
from rio_tiler.constants import WEB_MERCATOR_TMS
from rio_tiler.io import BaseReader, COGReader

from cogeo_mosaic.backends.base import (
    BaseBackend,
    mode_validator,
    update_zoom_and_bounds,
)
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class InMemoryBackend(BaseBackend):
    """InMemory Backend Adapter

    Examples:
        >>> with InMemory(mosaicJSON) as mosaic:
                mosaic.tile(0, 0, 0)

    """

    mosaic_def: MosaicJSON = attr.ib(on_setattr=update_zoom_and_bounds)  # type: ignore
    reader: Type[BaseReader] = attr.ib(default=COGReader)
    reader_options: Dict = attr.ib(factory=dict)
    backend_options: Dict = attr.ib(factory=dict)

    # TMS is outside the init because mosaicJSON and cogeo-mosaic only
    # works with WebMercator (mercantile) for now.
    tms: TileMatrixSet = attr.ib(init=False, default=WEB_MERCATOR_TMS)

    bounds: Tuple[float, float, float, float] = attr.ib(
        init=False, default=(-180, -90, 180, 90)
    )
    minzoom: int = attr.ib(init=False, default=0)
    maxzoom: int = attr.ib(init=False, default=30)

    path: str = attr.ib(init=False, default=":memory:")
    mode: str = attr.ib(init=False, default="w", validator=mode_validator)

    _backend_name = "MEM"
    _available_modes: List[str] = ["w"]

    def __attrs_post_init__(self):
        """Post Init."""
        self.minzoom = self.mosaic_def.minzoom
        self.maxzoom = self.mosaic_def.maxzoom
        self.bounds = self.mosaic_def.bounds

    def write(self, mosaic: MosaicJSON, overwrite: bool = True):
        """Write mosaicjson document."""
        if not isinstance(mosaic, MosaicJSON):
            mosaic = MosaicJSON(**dict(mosaic))
        self.mosaic_def = mosaic

    def _read(self) -> MosaicJSON:
        raise NotImplementedError("InMemoryBackend is a Write-Only backend.")
