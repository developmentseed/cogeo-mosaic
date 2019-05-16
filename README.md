# cogeo-mosaic

A lightweight and custom COG mosaic server based on [mosaicJSON](https://github.com/developmentseed/mosaicjson-spec).

![mosaicJSON](https://user-images.githubusercontent.com/10407788/57888417-1fc75100-7800-11e9-93a3-b54d06fb4cd2.png)

## Install
```
$ pip install http://github.com/developmentseed/cogeo-mosaic
```

## CLI

```
$ cogeo-mosaic --help
Usage: cogeo-mosaic [OPTIONS] COMMAND [ARGS]...

  cogeo_mosaic cli.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  create  Create mosaic definition from list of files
  run     Local Server
```

```
$ cogeo-mosaic create --help
Usage: cogeo-mosaic create [OPTIONS] [INPUT_FILES]

  Create mosaic definition file.

Options:
  -o, --output PATH  Output file name
  --threads INTEGER  threads
  --help             Show this message and exit.
 ```

#### Example
`$ cat list.txt | cogeo-mosaic create - | gzip > mosaic.json.gz`

## Usage

see [/demo](/demo)

## API

see [API.md](/doc/API.md)

## Deployment

#### Package Lambda

Create `package.zip`

```bash
$ docker-compose build --no-cache
$ docker-compose run --rm package
```

#### Deploy to AWS


```bash
$ brew install terraform

# (optional) add terraform backend
# see https://github.com/developmentseed/terraform-state-store

# Set ${AWS_ACCESS_KEY_ID} and ${AWS_SECRET_ACCESS_KEY} in your env
$ terraform init

$ terraform apply
```

## Contribution & Development

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
