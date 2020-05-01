# cogeo-mosaic 2.0 to 3.0 migration guide

### MosaicJSON pydantic model


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