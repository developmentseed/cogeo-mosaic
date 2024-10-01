"""cogeo-mosaic In-Memory backend."""

import attr

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class MemoryBackend(BaseBackend):
    """InMemory Backend Adapter

    Examples:
        >>> with MemoryBackend(mosaicJSON) as mosaic:
                mosaic.tile(0, 0, 0)
    """

    # We put `input` outside the init method
    input: str = attr.ib(init=False, default=":memory:")

    _backend_name = "MEM"

    def write(self, overwrite: bool = True):
        """Write mosaicjson document."""
        pass

    def _read(self) -> MosaicJSON:
        pass
