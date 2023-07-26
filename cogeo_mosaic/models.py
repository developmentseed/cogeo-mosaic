"""cogeo-mosaic models."""

import warnings
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field


class Info(BaseModel):
    """Mosaic info responses."""

    bounds: Tuple[float, float, float, float] = Field((-180, -90, 180, 90))
    center: Optional[Tuple[float, float, int]] = None
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    name: Optional[str] = None
    quadkeys: List[str] = []
    tilematrixset: Optional[str] = None

    def __getitem__(self, item):
        """Access item like in Dict."""
        warnings.warn(
            "'key' access will has been deprecated and will be removed in cogeo-mosaic 8.0.",
            DeprecationWarning,
        )
        return self.__dict__[item]
