# cogeo-mosaic

[![CircleCI](https://circleci.com/gh/developmentseed/cogeo-mosaic.svg?style=svg)](https://circleci.com/gh/developmentseed/cogeo-mosaic)

**Read the official announcement https://medium.com/devseed/cog-talk-part-2-mosaics-bbbf474e66df**


Create and use mosaics of COGs based on [mosaicJSON](https://github.com/developmentseed/mosaicjson-spec).

![mosaicJSON](https://user-images.githubusercontent.com/10407788/57888417-1fc75100-7800-11e9-93a3-b54d06fb4cd2.png)

# What is this 

This repo is a combination of a python (>3) module and a serverless stack (AWS).

The python module provide a CLI to help create mosaicJSON localy.


## Install the python module + cli
```bash
$ pip install pip -U
$ pip install cython==0.28 # (ref: https://github.com/tilery/python-vtzero/issues/13)
$ pip install git+http://github.com/developmentseed/cogeo-mosaic

$ cogeo-mosaic
Usage: cogeo-mosaic [OPTIONS] COMMAND [ARGS]...

  cogeo_mosaic cli.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  create     Create mosaic definition from list of files
  footprint  Create geojson from list of files
  overview   [EXPERIMENT] Create COG overviews for a mosaic
  run        Local Server
```

**Note**: Starting with version 2.0, pygeos has replaced shapely and thus makes `libgeos` a requirement.

### Usage - Create Mosaic definition
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

#### Create a mosaic from OAM

```bash 
# Create Footprint
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic footprint | gist -p -f test.geojson

# Create Mosaic
$ curl https://api.openaerialmap.org/user/5d6a0d1a2103c90007707fa0 | jq -r '.results.images[] | .uuid' | cogeo-mosaic create - | gzip >  5d6a0d1a2103c90007707fa0.json.gz
```

## Serverless Stack

A AWS Lambda function handler is included in this module.

### Deployment

#### Package Lambda

Create `package.zip`

```bash
$ docker-compose build --no-cache
$ docker-compose run --rm package
```

#### Deploy to AWS

This project uses [Serverless](https://serverless.com) to manage deploy on AWS.

```bash
# Install and Configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
$ npm install serverless -g 

$ sls deploy --region us-east-1 --bucket a-bucket-where-you-store-data
```

#### Docs

See [/doc/API.md](/doc/API.md) for the documentation. 

#### Live

A version of this stack is deployed on AWS us-east-1 and available on [cogeo.xyz](https://cogeo.xyz)

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
