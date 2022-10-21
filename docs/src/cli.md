
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
  info                  Return info about the mosaic
  to-geojson            Create GeoJSON from a MosaicJSON document
  update                Update a mosaic definition from list of files
  upload                Upload mosaic definition to backend
```

## Create

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

**[INPUT_FILES]** must be a list of valid Cloud Optimized GeoTIFF.

```bash
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
$ curl https://earth-search.aws.element84.com/collections/landsat-8-l1/items | \
    cogeo-mosaic create-from-features --minzoom 7 --maxzoom 12 --property "landsat:scene_id" --quiet | \
    jq

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
