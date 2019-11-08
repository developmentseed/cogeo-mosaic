"""custom pixel selection method."""

import numpy
from rio_tiler_mosaic.methods.base import MosaicMethodBase


class bidx_stddev(MosaicMethodBase):
    """Return bands stddev."""

    def __init__(self):
        """Overwrite base and init bands stddev method."""
        super(bidx_stddev, self).__init__()
        self.exit_when_filled = True

    def feed(self, tile):
        """Add data to tile."""
        tile = numpy.ma.std(tile, axis=0, keepdims=True)
        if self.tile is None:
            self.tile = tile

        pidex = self.tile.mask & ~tile.mask
        mask = numpy.where(pidex, tile.mask, self.tile.mask)
        self.tile = numpy.ma.where(pidex, tile, self.tile)
        self.tile.mask = mask
