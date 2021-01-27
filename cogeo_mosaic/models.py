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


class Metadata(RioTilerBaseModel):
    """MosaicJSON model.

    Based on https://github.com/developmentseed/mosaicjson-spec

    """

    mosaicjson: str
    name: Optional[str]
    description: Optional[str]
    version: str = "1.0.0"
    attribution: Optional[str]
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    quadkey_zoom: Optional[int]
    bounds: Tuple[float, float, float, float] = Field((-180, -90, 180, 90))
    center: Optional[Tuple[float, float, int]]

    class Config:
        """Model configuration."""

        extra = "ignore"
