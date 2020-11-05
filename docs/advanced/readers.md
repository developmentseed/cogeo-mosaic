

## COGReader / STACReader

The MosaicJSON backend classes have `.tile` and `.point` methods to access the data for a specific mercator tile or point.

Because a MosaicJSON can host different assets type, a `reader` option is available.
Set by default to `rio_tiler.io.COGReader`, or to `rio_tiler.io.STACReader` for the STACBackend, the reader should know how to read the assets to either create mosaic tile or read points value.

```python
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.backends import MosaicBackend
from rio_tiler.models import ImageData

dataset = ["1.tif", "2.tif"]
mosaic_definition = MosaicJSON.from_urls(dataset)

# Create a mosaic object in memory
with MosaicBackend(None, mosaid_def=mosaic_definition, reader=COGReader) as mosaic:
    img, assets_used = mosaic.tile(1, 1, 1)
    assert isinstance(img, ImageData)

# By default the STACbackend will store the Item url as assets, but STACReader (default reader) will know how to read them.
with MosaicBackend(
  "stac+https://my-stac.api/search",
  {"collections": ["satellite"]},
  7,  # minzoom
  12, # maxzoom
) as mosaic:
    img, assets_used = mosaic.tile(1, 1, 1, assets="red")
```

Let's use a custom accessor to save some specific assets url in the mosaic

```python
# accessor to return the url for the `visual` asset (COG)
def accessor(item):
    return feature["assets"]["visual"]["href"]

# The accessor will set the mosaic assets as a list of COG url so we can use the COGReader instead of the STACReader
with MosaicBackend(
  "stac+https://my-stac.api/search",
  {"collections": ["satellite"]},
  7,  # minzoom
  12, # maxzoom
  reader=COGReader,
  backend_options={"accessor": accessor},
) as mosaic:
    img, assets_used = mosaic.tile(1, 1, 1)
```
