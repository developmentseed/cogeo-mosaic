"""cogeo-mosaic models."""

from typing import List, Optional, Tuple

from pydantic import Field
from rio_tiler.models import RioTilerBaseModel


class Info(RioTilerBaseModel):
    """Mosaic info responses."""

    bounds: Tuple[float, float, float, float] = Field((-180, -90, 180, 90))
    center: Optional[Tuple[float, float, int]]
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    name: Optional[str]
    quadkeys: List[str] = []
