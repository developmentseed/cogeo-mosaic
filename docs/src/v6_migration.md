# cogeo-mosaic 5.0 to 6.0 migration guide

### MosaicJSON specification `0.0.3`

Starting with `6.0`, cogeo-mosaic will follow the MosaicJSON [`0.0.3`](https://github.com/developmentseed/mosaicjson-spec/tree/main/0.0.3) specification ([changes](https://github.com/developmentseed/mosaicjson-spec/blob/main/CHANGES.md#003-2023-05-31)). Old mosaic files should still be usable.

If updating a previous mosaic file, a warning should be printed.

### Multiple TileMatrixSets support (create)

Following specification `0.0.3`, we can now create Mosaics using other TileMatrixSet than the default `WebMercatorQuad`.

```python

import morecantile
from cogeo_mosaic.mosaic import MosaicJSON

tms_5041 = morecantile.tms.get("UPSArcticWGS84Quad")
mosaic = MosaicJSON.from_urls([...], tilematrixset=tms_5041)
assert mosaic.tilematrixset.id == "UPSArcticWGS84Quad"
```

### Multiple TileMatrixSets support in Backend (read)

You can now pass `TileMatrixSet` as input parameters to MosaicBackend to read tiles in other TileMatrixSet than the default `WebMercatorQuad`.

```python
import morecantile
from cogeo_mosaic.backends import MosaicBackend

tms = morecantile.tms.get("WGS1984Quad")
with MosaicBackend(mosaic_path, tms=tms) as mosaic:
    img, assets = mosaic.tile(1, 2, 3)
    assert img.crs == "epsg:4326"
```

Note: When passing a different TileMatrixSet than the mosaic's TileMatrixSet, the `minzoom/maxzoom` will default to the TileMatrixSet levels.
