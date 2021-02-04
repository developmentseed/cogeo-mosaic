

Starting in version `3.0.0`, we introduced specific backend storage for:

#### Read-Write Backends

- **File** (default, `file:///`)

- **AWS S3** (`s3://`)

- **AWS DynamoDB** (`dynamodb://{region}/{table_name}`). If `region` is not passed, it reads the value of the `AWS_REGION` environment variable. If that environment variable does not exist, it falls back to `us-east-1`. If you choose not to pass a `region`, you still need three `/` before the table name, like so `dynamodb:///{table_name}`.

- **SQLite** (`sqlite:///{file.db}:{mosaic_name}`)

#### Read Only Backends

Read only backend won't allow `mosaic_def` in there `__init__` method. `.write()` and `.update` methods will raise `NotImplementedError` error.

- **HTTP/HTTPS** (`http://`, `https://`)
- **STAC** (`stac+:https://`). Based on [SpatioTemporal Asset Catalog](https://github.com/radiantearth/stac-spec) API.

#### InMemory

If you have a mosaicjson document and want to use the different backend methods you can use the spetial `InMemoryBackend`.

```python
with InMemoryBackend(mosaic_def=mosaicjson) as mosaic:
    img = mosaic.tile(1, 1, 1)
```


## MosaicBackend

To ease the usage we added a helper function to use the right backend based on the uri schema: `cogeo_mosaic.backends.MosaicBackend`

```python
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.s3.S3Backend)

with MosaicBackend("dynamodb://us-east-1/amosaic") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.dynamodb.DynamoDBBackend)

with MosaicBackend("sqlite:///mosaic.db:amosaic") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.sqlite.SQLiteBackend)

with MosaicBackend("file:///amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.file.FileBackend)

with MosaicBackend("amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.file.FileBackend)

# Read-Only
with MosaicBackend("https://mosaic.com/amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.web.HttpBackend)

with MosaicBackend("stac+https://my-stac.api/search", {"collections": ["satellite"]}, 10, 12) as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.stac.STACBackend)

# In Memory (write)
with MosaicBackend(":memory:", mosaic_def=mosaic) as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.memory.InMemoryBackend)

with MosaicBackend(None, mosaic_def=mosaic) as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.stac.InMemoryBackend)
```

## STAC Backend

The STACBackend is a **read-only** backend, meaning it can't be used to write a file. This backend will POST to the input url looking for STAC items which will then be used to create the mosaicJSON in memory.

```python
import datetime
import mercantile
from cogeo_mosaic.backends.stac import STACBackend


geojson = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              30.810813903808594,
              29.454247067148533
            ],
            [
              30.88600158691406,
              29.454247067148533
            ],
            [
              30.88600158691406,
              29.51879923863822
            ],
            [
              30.810813903808594,
              29.51879923863822
            ],
            [
              30.810813903808594,
              29.454247067148533
            ]
          ]
        ]
      }
    }
  ]
}


date_min="2019-01-01"
date_max="2019-12-11"

start = datetime.datetime.strptime(date_min, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
end = datetime.datetime.strptime(date_max, "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

query = {
    "collections": ["sentinel-s2-l2a-cogs"],
    "datetime": f"{start}/{end}",
    "query": {
        "eo:cloud_cover": {
            "lt": 5
        }
    },
    "intersects": geojson["features"][0]["geometry"],
    "limit": 1000,
    "fields": {
      'include': ['id', 'properties.datetime', 'properties.data_coverage'],
      'exclude': ['assets']
    }
}

with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    query,
    8,
    15,
) as mosaic:
    print(mosaic.metadata)
```

#### Specification

The STACBackend rely on Spec version 1.0.0alpha.

#### Paggination

The returned object from the POST requests might not represent the whole results and thus
we need to use the paggination.

You can limit the pagination by using `max_items` or `stac_query_limit` options.

- Limit the total result to 1000 items

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    max_items=1000,
) as mosaic:
    print(mosaic.metadata)
```

- Limit the size of each POST result

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    stac_query_limit=500,
) as mosaic:
    print(mosaic.metadata)
```
Warnings: trying to run the previous example will results in fetching the whole collection.


#### Tile's asset

MosaicJSON tile asset is defined using `accessor` option. By default the backend will try to construct or retrieve the Item url

```python
def default_stac_accessor(feature: Dict):
    """Return feature identifier."""
    link = list(filter(lambda link: link["rel"] == "self", feature["links"]))
    if link:
        return link[0]["href"]

    link = list(filter(lambda link: link["rel"] == "root", feature["links"]))
    if link:
        return os.path.join(
            link[0]["href"],
            "collections",
            feature["collection"],
            "items",
            feature["id"],
        )

    # Fall back to the item ID
    return feature["id"]
```

This default accessor function rely on the `self` or `root` link to be present.

It's let to the user to built a Mosaic Tiler which will understand the asset.

#### Custom accessor

Accessor HAVE to be a callable which take a GeoJSON feature as input.

Here is an example of an accessor that will return the ulr for asset `B01`

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    stac_query_limit=500,
    accessor=lambda x: x["assets"]["B01"]["href"],
) as mosaic:
    print(mosaic.metadata)
```
