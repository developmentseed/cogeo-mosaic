"""cogeo-mosaic models."""

from typing import List, Optional, Tuple

from pydantic import Field
from rio_tiler.mosaic.backend import MosaicInfo


class Info(MosaicInfo):
    """Mosaic info responses."""

    center: Optional[Tuple[float, float, int]] = None
    name: Optional[str] = None
    quadkeys: List[str] = []
    mosaic_tilematrixset: Optional[str] = None
    mosaic_minzoom: int = Field(0, ge=0, le=30)
    mosaic_maxzoom: int = Field(30, ge=0, le=30)
