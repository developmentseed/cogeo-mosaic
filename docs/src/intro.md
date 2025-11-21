

**cogeo-mosaic** is set of [CLI](/CLI) and API to create, store and read [MosaicJSON](https://github.com/developmentseed/mosaicjson-spec) documents.


### MosaicJSON Model

cogeo-mosaic uses [Pydantic](https://pydantic-docs.helpmanual.io) model to store and validate mosaicJSON documents.
```python
class MosaicJSON(BaseModel):
    mosaicjson: str
    name: Optional[str]
    description: Optional[str]
    version: str = "1.0.0"
    attribution: Optional[str]
    minzoom: int = Field(0, ge=0, le=30)
    maxzoom: int = Field(30, ge=0, le=30)
    quadkey_zoom: Optional[int]
    bounds: List[float] = Field([-180, -90, 180, 90])
    center: Optional[Tuple[float, float, int]]
    tiles: Dict[str, List[str]]
    tilematrixset: Optional[morecantile.TileMatrixSet]
    asset_type: Optional[str]
    asset_prefix: Optional[str]
    data_type: Optional[str]
    colormap: Optional[Dict[int, Tuple[int, int, int, int]]]
    layers: Optional[Dict]
```

The model is based on the mosaicjson specification: https://github.com/developmentseed/mosaicjson-spec

Pydantic models are python classes which are extansible. Here is an example of how we can use the MosaicJSON model to create a mosaic from a list of COG urls:

```python
from cogeo_mosaic.mosaic import MosaicJSON

# list of COG
dataset = ["1.tif", "2.tif"]
mosaic_definition = MosaicJSON.from_urls(dataset)

print(mosaic_definition.tiles)
> {"tile": {"00001": ["cog1.tif", "2.tif"]}}
```

Lear more on MosaicJSON class [API/mosaic](../API/mosaic).


### Backends

MosaicJSON `backends` are python classes, based on rio-tiler [BaseBackend](https://github.com/cogeotiff/rio-tiler/blob/main/rio_tiler/mosaic/backend.py), which are used to interact with MosaicJSON documents, stored on AWS DynamoDB, AWS S3, locally, or on the web (http://).

Because each Backends extend rio-tiler [BaseBackend](https://github.com/cogeotiff/rio-tiler/blob/main/rio_tiler/mosaic/backend.py) they share the same minimal methods/properties

```python
from cogeo_mosaic.backends import MosaicJSONBackend
print(MosaicJSONBackend.__bases__)
>> (<class 'rio_tiler.mosaic.backend.BaseBackend'>,)
```

```python
from cogeo_mosaic.backends.s3 import S3Backend

# Read
with S3Backend("s3://mybucket/amosaic.json") as mosaic:
    mosaic.input                                   # attribute - MosaicJSON path
    mosaic.mosaic_def                              # attribute - MosaicJSON document, wrapped in a Pydantic Model
    mosaic.reader                                  # attribute - BaseReader, MultiBaseReader, MultiBandReader to use to fetch tile data
    mosaic.reader_options                          # attribute - Options for forward to `reader`
    mosaic.tms                                     # attribute - TileMatrixSet (default to WebMercatorQuad)
    mosaic.minzoom                                 # attribute - Mosaic (default to tms or mosaic minzoom)
    mosaic.maxzoom                                 # attribute - Mosaic (default to tms or mosaic maxzoom)

    mosaic.crs                                     # property - CRS (from mosaic's TMS geographic CRS)
    mosaic.bounds                                  # property - Mosaic bounds in `mosaic.crs`

    mosaic.mosaicid                                # property - Return sha224 id from the mosaicjson doc
    mosaic.quadkey_zoom                            # property - Return Quadkey zoom of the mosaic

    mosaic.write()                                 # method - Write the mosaicjson to the given location
    mosaic.update([features])                      # method - Update the mosaicjson data with a list of features

    mosaic.info(quadkeys=True/False)               # method -  spatial_info, list of quadkeys and mosaic name

    mosaic.get_geographic_bounds(crs: CRS)         # method - Return mosaic bounds in a geographic CRS

    mosaic.assets_for_tile(x, y, z)                # method - Find assets for a specific mercator tile
    mosaic.assets_for_point(lng, lat)              # method - Find assets for a specific point
    mosaic.assets_for_bbox(xmin, ymin, xmax, ymax) # method - Find assets for a specific bbox

    mosaic.tile(1,2,3)                             # method - Create mosaic tile
    mosaic.point(lng, lat)                         # method - Read point value from multiple assets
    mosaic.part(bbox)                              # method - Create image from part of multiple assets
    mosaic.feature(feature)                        # method - Create image from GeoJSON feature of multiple assets
```

!!! Important

    `statistics()`, `preview()` methods are not implemented in BaseBackend

#### Open Mosaic and Get assets list for a tile

```python
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    assets: List[str] = mosaic.assets_for_tile(1, 2, 3) # get assets for morecantile.Tile(1, 2, 3)
```

!!! Important

    `MosaicBackend` is a function which returns the correct `backend` by checking the path/url schema.

    see [MosaicBackend](https://developmentseed.org/cogeo-mosaic/advanced/backends/#mosaicbackend)

#### Open Mosaic and get Tile Data (mosaic tile)

```python
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    img: ImageData, assets_used: List[str] = mosaic.tile(1, 2, 3)
```

#### Write Mosaic

```python
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.backends import MosaicBackend

# Create a MosaicJSON
mosaicdata = MosaicJSON.from_urls(["1.tif", "2.tif"])

with MosaicBackend("s3://mybucket/amosaic.json", mosaic_def=mosaicdata) as mosaic:
    mosaic.write() # trigger upload to S3
```

#### Update a Mosaic

```python
from cogeo_mosaic.utils import get_footprints
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    features = get_footprints(["3.tif"]) # Get footprint
    mosaic.update(features) # Update mosaicJSON and upload to S3
```

### In Memory Mosaic

```python
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.backends import MosaicBackend

from cogeo_mosaic.backends.memory import MemoryBackend

mosaic_definition = MosaicJSON.from_urls(["1.tif", "2.tif"])

# If set to None or :memory:, MosaicBackend will use the MemoryBackend
with MosaicBackend(":memory:", mosaic_def=mosaicdata) as mosaic:
    assert isinstance(mosaic, MemoryBackend)
    img, assets_used = mosaic.tile(1, 2, 3)

with MosaicBackend(None, mosaic_def=mosaicdata) as mosaic:
    assert isinstance(mosaic, MemoryBackend)
    img, assets_used = mosaic.tile(1, 2, 3)

with MemoryBackend(mosaic_def=mosaicdata) as mosaic:
    img, assets_used = mosaic.tile(1, 2, 3)
```

### TileMatrixSet attribute

```python
from cogeo_mosaic.backends import MosaicBackend
import morecantile

# Mosaic in WebMercatorQuad (default), output tile in WGS84
WGS1984Quad = morecantile.tms.get("WGS1984Quad")

with MosaicBackend("s3://mybucket/amosaic.json", tms=WGS1984Quad) as mosaic:
    img: ImageData, assets_used: List[str] = mosaic.tile(1, 2, 3)

    # The mosaic might use a specific TMS (WebMercatorQuad by default)
    assert mosaic.mosaic_def.tilematrixset.rasterio_crs == "epsg:3857"

    # When passing `tms=`, the output tile image will have the CRS from the input TMS
    assert img.crs == "epsg:4326"
```

# Image Order

**By default the order of the dataset, either passed via the CLI or in the API, defines the order of the quadkey's assets.**

```python
from cogeo_mosaic.mosaic import MosaicJSON

# list of COG
dataset = ["1.tif", "2.tif"]
mosaic_definition = MosaicJSON.from_urls(dataset)

print(mosaic_definition.tiles)
> {"tile": {"0": ["1.tif", "2.tif"]}}
```
