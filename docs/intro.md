
#### Intro

# Placeholder


##### Using Backends

Each MosaicBackends (file, http, s3, dynamodb and stac) extend rio-tiler [BaseReader](https://github.com/cogeotiff/rio-tiler/blob/master/rio_tiler/io/base.py#L16) and thus derives the same minimal methods/properties

```python
from cogeo_mosaic.backends import MosaicBackend

# Read
with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    mosaic.mosaic_def                  # property - MosaicJSON document, wrapped in a Pydantic Model
    mosaic.metadata                    # property - Return mosaic metadata
    mosaic.mosaicid                    # property - Return sha224 id from the mosaicjson doc
    mosaic.quadkey_zoom                # property - Return Quadkey zoom of the mosaic

    mosaic.minzoom                     # property - Mosaic minzoom
    mosaic.maxzoom                     # property - Mosaic maxzoom
    mosaic.bounds                      # property - Mosaic bounds
    mosaic.spatial_info                # property - zooms and bounds info

    mosaic.info                        # method -  spatial_info, list of quadkeys and mosaic name

    mosaic.assets_for_tile(1,2,3)      # method - Find assets for a specific mercator tile
    mosaic.assets_for_point(lng, lat)  # method - Find assets for a specific point

    mosaic.tile(1,2,3)                 # method - Create mosaic tile
    mosaic.point(lng, lat)             # method - Read point value from multiple assets
    mosaic.write()                     # method - Write the mosaicjson to the given location
    mosaic.update([features])          # method - Update the mosaicjson data with a list of features
```

##### Read and Get assets list
```python
# MosaicBackend is the top level backend and will distribute to the
# correct backend by checking the path/url schema.
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    assets: List = mosaic.assets_for_tile(1, 2, 3) # get assets for mercantile.Tile(1, 2, 3)
```

##### Read Tile Data (mosaic tile)
```python
# MosaicBackend is the top level backend and will distribute to the
# correct backend by checking the path/url schema.
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    tile, mask = mosaic.tile(1, 2, 3)
```

##### Write
```python
from cogeo_mosaic.utils import create_mosaic
from cogeo_mosaic.backends import MosaicBackend

mosaicdata = create_mosaic(["1.tif", "2.tif"])

with MosaicBackend("s3://mybucket/amosaic.json", mosaic_def=mosaicdata) as mosaic:
    mosaic.write() # trigger upload to S3
```

##### Update
```python
from cogeo_mosaic.utils import get_footprints
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    features = get_footprints(["3.tif"]) # Get footprint
    mosaic.update(features) # Update mosaicJSON and upload to S3
```

#### In Memory
```python
from cogeo_mosaic.utils import create_mosaic
from cogeo_mosaic.backends import MosaicBackend

mosaicdata = create_mosaic(["1.tif", "2.tif"])

with MosaicBackend(None, mosaic_def=mosaicdata) as mosaic:
    tile, mask = mosaic.tile(1, 2, 3)
```


# Image Order

**By default the order of the dataset, either passed via the CLI or in the API, defines the order of the quadkey's assets.**

```python
from cogeo_mosaic.mosaic import MosaicJSON

# list of COG
dataset = ["1.tif", "2.tif"]
mosaic_definition = MosaicJSON.from_urls(dataset)

print(mosaic_definition.tiles)
> {"tile": {"0": ["cog1.tif", "2.tif"]}}
```
