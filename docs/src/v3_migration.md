# cogeo-mosaic 2.0 to 3.0 migration guide

### MosaicJSON pydantic model

We now use [pydantic](https://pydantic-docs.helpmanual.io) to define the MosaicJSON document. Pydantic

From Pydantic docs:
> Define how data should be in pure, canonical python; validate it with pydantic.

Pydantic model enforce the mosaicjson specification for the whole project by validating each items.

```python
from pydantic import BaseModel

class MosaicJSON(BaseModel):
    """
    MosaicJSON model.

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
    bounds: List[float] = Field([-180, -90, 180, 90])
    center: Optional[Tuple[float, float, int]]
    tiles: Dict[str, List[str]]
```

##### Validation

```python
mosaic_definition = dict(
    mosaicjson="0.0.2",
    minzoom=1,
    maxzoom=2,
    quadkey_zoom=1,
    bounds=[-180, -90, 180, 90],
    center=(0, 0, 1),
    tiles={},
)

m = MosaicJSON(**mosaic_definition)
> MosaicJSON(mosaicjson='0.0.2', name=None, description=None, version='1.0.0', attribution=None, minzoom=1, maxzoom=2, quadkey_zoom=1, bounds=[-180.0, -90.0, 180.0, 90.0], center=(0.0, 0.0, 1), tiles={})
```

```python
# convert the mode to a dict
m.dict(exclude_none=True)
> {'mosaicjson': '0.0.2',
 'version': '1.0.0',
 'minzoom': 1,
 'maxzoom': 2,
 'quadkey_zoom': 1,
 'bounds': [-180.0, -90.0, 180.0, 90.0],
 'center': (0.0, 0.0, 1),
 'tiles': {}}
```

```python
mosaic_definition = dict(
    mosaicjson="0.0.2",
    minzoom=1,
    maxzoom=100,
    quadkey_zoom=1,
    bounds=[-180, -90, 180, 90],
    center=(0, 0, 1),
    tiles={},
)

m = MosaicJSON(**mosaic_definition)
...
ValidationError: 1 validation error for MosaicJSON
maxzoom
  ensure this value is less than or equal to 30 (type=value_error.number.not_le; limit_value=30)
```

### Creation

The `MosaicJSON` class comes also with helper functions:
- **MosaicJSON.from_urls**: Create a mosaicjson from a set of COG urls
- **MosaicJSON.from_features**: Create a mosaicjson from a set of GeoJSON features
- **MosaicJSON._create_mosaic** (semi-private): Low level mosaic creation methods used by public methods (`from_urls` and `from_features`).

```python
#V2
from cogeo_mosaic.utils import create_mosaic

mosaic_definition: Dict = create_mosaic(dataset)


#V3
from cogeo_mosaic.mosaic import MosaicJSON

mosaic_definition: MosaicJSON = MosaicJSON.from_urls(dataset)

# or from a list of GeoJSON Features
mosaic_definition: MosaicJSON = MosaicJSON.from_features(dataset, minzoom=1, maxzoom=3)
```


To learn more about the low-level api checkout [/docs/AdvancedTopics.md](/docs/AdvancedTopics.md)

### Backend Storage

#### Read
```python
# V2
from cogeo_mosaic.utils import (
    fetch_mosaic_definition,
    fetch_and_find_assets,
    fetch_and_find_assets_point,
)
mosaic_definition = fetch_mosaic_definition(url)
assets = fetch_and_find_assets(url, x, y, z)
assets = fetch_and_find_assets_point(url, lng, lat)


# V3
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend(url) as mosaic:
    mosaic_definition = mosaic.mosaic_def
    assets = mosaic.tile(x, y, z)    # LRU cache
    assets = mosaic.point(lng, lat)  # LRU cache
```

#### Write
```python

#V2
from cogeo_mosaic.utils import create_mosaic
from boto3.session import Session as boto3_session

mosaic_definition = create_mosaic(dataset)

def _compress_gz_json(data):
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    return (
        gzip_compress.compress(json.dumps(data).encode("utf-8")) + gzip_compress.flush()
    )

session = boto3_session()
client = session.client("s3")
client.put_object(
    Bucket=bucket,
    Key=key,
    Body=_compress_gz_json(mosaic_definition),
)

#V3
from cogeo_mosaic.mosaic import MosaicJSON

mosaic_definition = MosaicJSON.from_urls(dataset)

with MosaicBackend("s3://{bucket}/{key}", mosaic_def=mosaic_definition) as mosaic:
    mosaic.write()
```
