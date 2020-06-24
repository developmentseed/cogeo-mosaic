# cogeo-mosaic

Create mosaics of Cloud Optimized GeoTIFF based on [mosaicJSON](https://github.com/developmentseed/mosaicjson-spec) specification.

[![PyPI pyversions](https://img.shields.io/pypi/pyversions/cogeo-mosaic.svg)](https://pypi.python.org/pypi/ansicolortags/)
[![Packaging status](https://badge.fury.io/py/cogeo-mosaic.svg)](https://badge.fury.io/py/cogeo-mosaic)
[![CircleCI](https://circleci.com/gh/developmentseed/cogeo-mosaic.svg?style=svg)](https://circleci.com/gh/developmentseed/cogeo-mosaic)
[![codecov](https://codecov.io/gh/developmentseed/cogeo-mosaic/branch/master/graph/badge.svg)](https://codecov.io/gh/developmentseed/cogeo-mosaic)

![cogeo-mosaic](https://user-images.githubusercontent.com/10407788/73185274-c41dc900-40eb-11ea-8b67-f79c0682c3b0.jpg)

**Read the official announcement https://medium.com/devseed/cog-talk-part-2-mosaics-bbbf474e66df**

This python module provide a CLI to help create mosaicJSON.

## Install (python >=3)
```bash
$ pip install pip -U
$ pip install cogeo-mosaic

# Or from source

$ pip install git+http://github.com/developmentseed/cogeo-mosaic
```

**Notes**:
- Starting with version 2.0, pygeos has replaced shapely and thus makes `libgeos` a requirement.
- **pygeos** hosted on pypi migth not compile on certain machine. This has been fixed in the master branch and can be installed with `pip install git+https://github.com/pygeos/pygeos.git`

# CLI
```
$ cogeo-mosaic --help
Usage: cogeo-mosaic [OPTIONS] COMMAND [ARGS]...

  cogeo_mosaic cli.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  create                Create mosaic definition from list of files
  create-from-features  Create mosaic definition from GeoJSON features or features collection
  footprint             Create geojson from list of files
  overview              [EXPERIMENTAL] Create a low resolution version of a mosaic
  update                Update a mosaic definition from list of files
```

### Create Mosaic definition
```bash
$ cogeo-mosaic create --help
Usage: cogeo-mosaic create [OPTIONS] [INPUT_FILES]

  Create mosaic definition file.

Options:
  -o, --output PATH       Output file name
  --minzoom INTEGER       An integer to overwrite the minimum zoom level derived from the COGs.
  --maxzoom INTEGER       An integer to overwrite the maximum zoom level derived from the COGs.
  --quadkey-zoom INTEGER  An integer to overwrite the quadkey zoom level used for keys in the MosaicJSON.
  --min-tile-cover FLOAT  Minimum % overlap
  --tile-cover-sort       Sort files by covering %
  --threads INTEGER       threads
  -q, --quiet             Remove progressbar and other non-error output.
  --help                  Show this message and exit.
 ```

`[INPUT_FILES]` must be a list of valid Cloud Optimized GeoTIFF.

```
$ cogeo-mosaic create list.txt -o mosaic.json

# or

$ cat list.txt | cogeo-mosaic create - | gzip > mosaic.json.gz

# or use backends like AWS S3 or DynamoDB

$ cogeo-mosaic create list.txt -o s3://my-bucket/my-key.json.gz
```

#### Example: create a mosaic from OAM

```bash
# Create Mosaic
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic create - | gzip >  5d6a0d1a2103c90007707fa0.json.gz

# Create Footprint (optional)
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic footprint | gist -p -f test.geojson
```

### Create Mosaic definition from a GeoJSON features collection (e.g STAC)

This module is first design to create mosaicJSON from a set of COG urls but starting in version `3.0.0` we have added a CLI to be able to create mosaicJSON from GeoJSON features.
```
$ cogeo-mosaic create-from-features --help
Usage: cogeo-mosaic create-from-features [OPTIONS] FEATURES...

  Create mosaic definition file.

Options:
  -o, --output PATH       Output file name
  --minzoom INTEGER       Mosaic minimum zoom level.  [required]
  --maxzoom INTEGER       Mosaic maximum zoom level.  [required]
  --property TEXT         Define accessor property  [required]
  --quadkey-zoom INTEGER  An integer to overwrite the quadkey zoom level used for keys in the MosaicJSON.
  --min-tile-cover FLOAT  Minimum % overlap
  --tile-cover-sort       Sort files by covering %
  -q, --quiet             Remove progressbar and other non-error output.
  --help                  Show this message and exit.
```

#### Use it with STAC

```bash
curl https://earth-search.aws.element84.com/collections/landsat-8-l1/items | cogeo-mosaic create-from-features --minzoom 7 --maxzoom 12 --property "landsat:scene_id" --quiet | jq

{
  "mosaicjson": "0.0.2",
  "version": "1.0.0",
  "minzoom": 7,
  "maxzoom": 12,
  "quadkey_zoom": 7,
  "bounds": [16.142300225571994, -28.513088675819393, 67.21380296165974, 81.2067478836583],
  "center": [41.67805159361586, 26.346829603919453, 7],
  "tiles": {
    "1012123": [
      "LC81930022020114LGN00"
    ],
    ...
  }
}
```

### Create Mosaic Overview [experimental]

The CLI provides an `overview` command to create low-resolution version of a mosaic.
This is hightly experimental and might incure some cost if you are hosting mosaic on DynamoDB or COG files on S3. To create the overview, the `overview` method will fetch all the asset's overviews (COG internal overview) and construct one or multiple COG .

```
$ cogeo-mosaic overview s3://bucket/mymosaic.json
```

![](https://user-images.githubusercontent.com/10407788/80844578-fa7c5000-8bd4-11ea-9eb8-5d1f84461dad.png)


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

# API
## Mosaic Storage Backends

Starting in version `3.0.0`, we introduced specific backend storage for:

- **File** (default, `file:///`)

- **HTTP/HTTPS/FTP** (`https://`, `https://`, `ftp://`)

- **AWS S3** (`s3://`)

- **AWS DynamoDB** (`dynamodb://{region}/{table_name}`). If `region` is not passed, it reads the value of the `AWS_REGION` environment variable. If that environment variable does not exist, it falls back to `us-east-1`. If you choose not to pass a `region`, you still need three `/` before the table name, like so `dynamodb:///{table_name}`.

- [WIP] **STAC** (`stac+:https://`). Based on [SpatioTemporal Asset Catalog](https://github.com/radiantearth/stac-spec) API.


To ease the usage we added a helper function to use the right backend based on the uri schema: `cogeo_mosaic.backends.MosaicBackend`

```python
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.s3.S3Backend)

with MosaicBackend("https://mosaic.com/amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.http.HttpBackend)

with MosaicBackend("dynamodb://us-east-1/amosaic") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.dynamodb.DynamoDBBackend)

with MosaicBackend("file:///amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.file.FileBackend)

with MosaicBackend("stac+https://my-stac.api/search", {"collections": ["satellite"]}) as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.stac.STACBackend)

with MosaicBackend("amosaic.json.gz") as mosaic:
    assert isinstance(mosaic, cogeo_mosaic.backends.file.FileBackend)
```

##### Properties and Methods
```python
from cogeo_mosaic.backends import MosaicBackend

# Read
with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    mosaic.mosaic_def         # property - MosaicJSON document, wrapped in a Pydantic Model
    mosaic.metadata           # property - Return mosaic metadata
    mosaic.mosaicid           # property - Return sha224 id from the mosaicjson doc
    mosaic.quadkey_zoom       # property - Return Quadkey zoom of the mosaic

    mosaic.tile(1,2,3)        # method - Find assets for a specific mercator tile
    mosaic.point(lng, lat)    # method - Find assets for a specific point
    mosaic.write()            # method - Write the mosaicjson to the given location
    mosaic.update([features]) # method - Update the mosaicjson data with a list of features
```

##### Read and Get assets
```python
# MosaicBackend is the top level backend and will distribute to the
# correct backend by checking the path/url schema.
from cogeo_mosaic.backends import MosaicBackend

with MosaicBackend("s3://mybucket/amosaic.json") as mosaic:
    assets: List = mosaic.tile(1, 2, 3) # get assets for mercantile.Tile(1, 2, 3)
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
    assets: List = mosaic.tile(1, 2, 3) # get assets for mercantile.Tile(1, 2, 3)
```

#### STAC: SpatioTemporal Asset Catalog

The STACBackend is purely dynamic, meaning it's not used to read or write a file. This backend will POST to the input url looking for STAC items which will then be used to create the mosaicJSON.

see [/docs/STAC_backend.md](/docs/STAC_backend.md) for more info.

# Associated Modules
- [**cogeo-mosaic-tiler**](http://github.com/developmentseed/cogeo-mosaic-tiler): A serverless stack to serve and vizualized tiles from Cloud Optimized GeoTIFF mosaic.

- [**cogeo-mosaic-viewer**](http://github.com/developmentseed/cogeo-mosaic-viewer): A local Cloud Optimized GeoTIFF mosaic viewer based on [rio-viz](http://github.com/developmentseed/rio-viz).

# Contribution & Development

Issues and pull requests are more than welcome.

**Dev install & Pull-Request**

```
$ git clone http://github.com/developmentseed/cogeo-mosaic.git
$ cd cogeo-mosaic
$ pip install -e .[dev]
```


**Python >=3.7 only**

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```
$ pre-commit install

$ git add .

$ git commit -m'my change'
isort....................................................................Passed
black....................................................................Passed
Flake8...................................................................Passed
Verifying PEP257 Compliance..............................................Passed
mypy.....................................................................Passed

$ git push origin
```

## About
Created by [Development Seed](<http://developmentseed.org>)
