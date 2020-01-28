# cogeo-mosaic

Create mosaics of Cloud Optimized GeoTIFF based on [mosaicJSON](https://github.com/developmentseed/mosaicjson-spec) specification.

[![Packaging status](https://badge.fury.io/py/cogeo-mosaic.svg)](https://badge.fury.io/py/cogeo-mosaic)
[![CircleCI](https://circleci.com/gh/developmentseed/cogeo-mosaic.svg?style=svg)](https://circleci.com/gh/developmentseed/cogeo-mosaic)
[![codecov](https://codecov.io/gh/developmentseed/cogeo-mosaic/branch/master/graph/badge.svg)](https://codecov.io/gh/developmentseed/cogeo-mosaic)

![cogeo-mosaic](https://user-images.githubusercontent.com/10407788/73185274-c41dc900-40eb-11ea-8b67-f79c0682c3b0.jpg)

**Read the official announcement https://medium.com/devseed/cog-talk-part-2-mosaics-bbbf474e66df**

This python module provide a CLI to help create mosaicJSON.

## Install
```bash
$ pip install pip -U
$ pip install cogeo-mosaic

# Or from source

$ pip install git+http://github.com/developmentseed/cogeo-mosaic
```

**Notes**: 
- Starting with version 2.0, pygeos has replaced shapely and thus makes `libgeos` a requirement.
- **pygeos** hosted on pypi migth not compile on certain machine. This has been fixed in the master branch and can be installed with `pip install git+https://github.com/pygeos/pygeos.git`

## Use
```
$ cogeo-mosaic --help
Usage: cogeo-mosaic [OPTIONS] COMMAND [ARGS]...

  cogeo_mosaic cli.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  create     Create mosaic definition from list of files
  footprint  Create geojson from list of files
  overview   [EXPERIMENT] Create COG overviews for a mosaic
```

### Create Mosaic definition
```bash
$ cogeo-mosaic create --help
Usage: cogeo-mosaic create [OPTIONS] [INPUT_FILES]

  Create mosaic definition file.

Options:
  -o, --output PATH  Output file name
  --threads INTEGER  threads
  --help             Show this message and exit.
 ```

`[INPUT_FILES]` must be a list of valid Cloud Optimized GeoTIFF.

```
$ cogeo-mosaic create list.txt -o mosaic.json

# or 

$ cat list.txt | cogeo-mosaic create - | gzip > mosaic.json.gz
```

#### Example: create a mosaic from OAM

```bash 
# Create Mosaic
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic create - | gzip >  5d6a0d1a2103c90007707fa0.json.gz

# Create Footprint (optional)
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic footprint | gist -p -f test.geojson
```

## Associated Modules
- [**cogeo-mosaic-tiler**](http://github.com/developmentseed/cogeo-mosaic-tiler): A serverless stack to serve and vizualized tiles from Cloud Optimized GeoTIFF mosaic.

- [**cogeo-mosaic-viewer**](http://github.com/developmentseed/cogeo-mosaic-viewer): A local Cloud Optimized GeoTIFF mosaic viewer based on [rio-viz](http://github.com/developmentseed/rio-viz).

### Contribution & Development

Issues and pull requests are more than welcome.

**Dev install & Pull-Request**

```
$ git clone http://github.com/developmentseed/cogeo-mosaic.git
$ cd cogeo-mosaic
$ pip install -e .[dev]
```


**Python >=3.6 only**

This repo is set to use `pre-commit` to run *flake8*, *pydocstring* and *black* ("uncompromising Python code formatter") when committing new code.

```
$ pre-commit install
$ git add .
$ git commit -m'my change'
black....................................................................Passed
Flake8...................................................................Passed
Verifying PEP257 Compliance..............................................Passed
$ git push origin
```

## About
Created by [Development Seed](<http://developmentseed.org>)
