## Unreleased

## 7.2.0 (2024-10-04)

* update BaseBackend to use a default coord_crs from the tms (author @AndrewAnnex, https://github.com/developmentseed/cogeo-mosaic/pull/234)
* add python 3.12 support
* Add tms parameter to cli for MosaicJSON (co-author @AndrewAnnex, https://github.com/developmentseed/cogeo-mosaic/pull/233)

## 7.1.0 (2023-12-06)

* Automatically remove/add `asset_prefix` in Mosaic Backends

## 7.0.1 (2023-10-17)

* add `py.typed` file (https://peps.python.org/pep-0561)

## 7.0.0 (2023-07-26)

* update `morecantile` requirement to `>=5.0,<6.0`
* update `rio-tiler` requirement to `>=6.0,<7.0`
* update `pydantic` requirement to `~=2.0`

## 6.2.0 (2023-07-11)

* add `coord_crs` to `MosaicBackend.point()` method

## 6.1.0 (2023-07-11)

* add `tilematrixset` in `MosaicBackend.info()` response

## 6.0.1 (2023-07-11)

* fix `HttpBackend` post_init method

## 6.0.0 (2023-07-10)

* update `morecantile>=4.1,<5.0` and `rio-tiler>=5.0,<6.0` requirements

* replace `supermercado` with [`supermorecado`](https://github.com/developmentseed/supermorecado) to burn geometries as tiles for different TMS

* update MosaicJSON models to `0.0.3` specification (adds `tilematrixset`, `asset_type`, `asset_prefix`, `data_type`, `colormap` and `layers` attributes)

* allow Mosaic creation using other TileMatrixSet (default is still `WebMercatorQuad`)

* add `tms` support to MosaicBackend to read tile in other TMS than the mosaic TileMatrixSet

    ```python
    # Before
    # Mosaic and output Tile in WebMercatorQuad
    with MosaicBackend("mosaic.json") as mosaic:
        img, _ = mosaic.tile(0, 0, 0)

    # Now
    # Mosaic in WebMercatorQuad (default), output tile in WGS84
    WGS1984Quad = morecantile.tms.get("WGS1984Quad")
    with MosaicBackend("mosaic.json", tms=WGS1984Quad) as mosaic:
        img, _ = mosaic.tile(0, 0, 0)
    ```

## 5.1.1 (2023-02-06)

* Clip dataset bounds with of TMS bbox (author @lseelenbinder, https://github.com/developmentseed/cogeo-mosaic/pull/200)

## 5.1.0 (2023-01-20)

* use `az://` prefix for private Azure Blob Storage Backend.

## 5.0.0 (2022-11-21)

* switch from pygeos to shapely>=2.0

## 4.2.2 (2022-11-19)

* remove useless file in package

## 4.2.1 (2022-11-15)

* add python 3.11 support

## 4.2.0 (2022-10-24)

* remove python 3.7 support
* add python 3.10 support
* switch to hatch build-system
* update rio-tiler dependency to >=4.0.0a0

## 4.1.1 (2022-10-21)

* Add Azure Blob Storage backend (author @christoe, https://github.com/developmentseed/cogeo-mosaic/pull/191)

## 4.1.0 (2022-02-22)

* remove `mercantile` and switch to morecantile>=3.1

## 4.0.0 (2021-11-30)

* no change since `4.0.0a2`

## 4.0.0a2 (2021-11-22)

* update rio-tiler requirement (`>=3.0.0a6`) and update backend reader type information

## 4.0.0a1 (2021-11-18)

* update rio-tiler requirement (`>=3.0.0a5`)
* fix `MosaicBackend` to match Backend input names.

## 4.0.0a0 (2021-10-20)

* update morecantile requirement to >= 3.0
* update rio-tiler requirement to >= 3.0 and update Backend's properties
* switch from `requests` to `httpx`
* add `BaseBackend.assets_for_bbox()` method (https://github.com/developmentseed/cogeo-mosaic/pull/184)

**breaking changes**

* remove `BaseBackend.metadata()` method (can be replaced by `BaseBackend.mosaic_def.dict(exclude={"tiles"})`)
* remove `cogeo_mosaic.models.Metadata` model
* remove python 3.6 support
* `BaseBackend.path` -> `BaseBackend.input` attribute (`input` was added in rio-tiler BaseReader)

## 3.0.2 (2021-07-08)

* Add Google Cloud Storage (`gs://...`) mosaic backend (author @AndreaGiardini, https://github.com/developmentseed/cogeo-mosaic/pull/179)

## 3.0.1 (2021-06-22)

* Make sure to pass an openned file to click.Progressbar (https://github.com/developmentseed/cogeo-mosaic/pull/178)

## 3.0.0 (2021-05-19)

* update rio-tiler version dependencies
* update pygeos dependency to >=0.10 which fix https://github.com/developmentseed/cogeo-mosaic/issues/81

## 3.0.0rc2 (2021-02-25)

**breaking**

* `gzip` is now only applied if the path endswith `.gz`
* remove `backend_options` attribute in base backends. This attribute was used to pass optional `gzip` option and/or STAC related options
* STAC backends has additional attributes (`stac_api_options` and `mosaic_options`)


## 3.0.0rc1 (2021-02-11)

* add `SQLite` backend (https://github.com/developmentseed/cogeo-mosaic/pull/148)
* fix cached responsed after updating a mosaic (https://github.com/developmentseed/cogeo-mosaic/pull/148/files#r557020660)
* update mosaicJSON.bounds type definition to match rio-tiler BaseReader definition (https://github.com/developmentseed/cogeo-mosaic/issues/158)
* add default bounds/minzoom/maxzoom values matching the mosaicjson default in the backends (https://github.com/developmentseed/cogeo-mosaic/pull/162)
* raise an error when trying to pass `mosaic_def` in read-only backend (https://github.com/developmentseed/cogeo-mosaic/pull/162)
* add `MemoryBackend` (https://github.com/developmentseed/cogeo-mosaic/pull/163)

**breaking**

* Updated the backends `.point()` methods to return a list in form of `[(asset1, values)]` (https://github.com/developmentseed/cogeo-mosaic/pull/168)

## 3.0.0b1 (2020-12-18)

* remove `overview` command (https://github.com/developmentseed/cogeo-mosaic/issues/71#issuecomment-748265645)
* remove `rio-cogeo` dependencies
* update rio-tiler version (`2.0.0rc4`)

## 3.0.0a19 (2020-12-14)

* Update to remove all calls to `rio_tiler.mercator` functions.

## 3.0.0a18 (2020-11-24)

* update Backend base class for rio-tiler 2.0.0rc3 (add `.feature()` method)

## 3.0.0a17 (2020-11-09)

* update for rio-tiler 2.0rc and add backend output models

## 3.0.0a16 (2020-10-26)

* raise `MosaicNotFoundError` when mosaic doesn't exists in the DynamoDB table.

## 3.0.0a15 (2020-10-22)

* fix typo in DynamoDB backend (https://github.com/developmentseed/cogeo-mosaic/pull/134)
* rename `cogeo_mosaic/backends/http.py` -> `cogeo_mosaic/backends/web.py` to avoid conflicts (author @kylebarron, https://github.com/developmentseed/cogeo-mosaic/pull/133)

## 3.0.0a14 (2020-10-22)

* add logger (`cogeo_mosaic.logger.logger`)
* Update STACBackend to better handler paggination (ref: https://github.com/developmentseed/cogeo-mosaic/pull/125)
* with change from #125, `stac_next_link_key` has be specified if you know the STAC API is using the latest specs:

```python
with MosaicBackend(
    f"stac+{stac_endpoint}",
    query.copy(),
    11,
    14,
    backend_options={
        "accessor": lambda feature: feature["id"],
        "stac_next_link_key": "next",
    }
) as mosaic:
```

* add `to-geojson` CLI to create a GeoJSON from a mosaicJSON document (#128)
* refactor internal cache (https://github.com/developmentseed/cogeo-mosaic/pull/131)
* add progressbar for iterating over quadkeys when creating a mosaic (author @kylebarron, https://github.com/developmentseed/cogeo-mosaic/pull/130)

### Breaking changes

* refactored DynamoDB backend to store multiple mosaics in one table (https://github.com/developmentseed/cogeo-mosaic/pull/127)
    - new path schema `dynamodb://{REGION}?/{TABLE}:{MOSAIC}`

* renamed exception `MosaicExists` to `MosaicExistsError`
* renamed option `fetch_quadkeys` to `quadkeys` in DynamoDBBackend.info() method
* add `quadkeys` option in `Backends.info()` to return (or not) the list of quadkeys (https://github.com/developmentseed/cogeo-mosaic/pull/129)
* moves `get_assets` to the base Backend (https://github.com/developmentseed/cogeo-mosaic/pull/131)
* remove multi_level mosaic support (https://github.com/developmentseed/cogeo-mosaic/issues/122)

## 3.0.0a13 (2020-10-13)

* add TMS in BaseBackend to align with rio-tiler BaseBackend.

## 3.0.0a12 (2020-10-07)

* remove pkg_resources (https://github.com/pypa/setuptools/issues/510)
* raise error when `minimum_tile_cover` is > 1 (https://github.com/developmentseed/cogeo-mosaic/issues/117)
* fix wrong indices sorting in default_filter (https://github.com/developmentseed/cogeo-mosaic/issues/118)

Note: We changed the versioning scheme to {major}.{minor}.{path}{pre}{prenum}

## 3.0a11 (2020-09-21)

* Raise Exception when trying to overwrite a mosaic (#112)
* Add `reverse` option in `.tile` and `.point` to get values from assets in reversed order.

## 3.0a10 (2020-08-24)

* Allow PointOutsideBounds exception for `point` method (#108)

## 3.0a9 (2020-08-24)

* BaseBackend.center returns value from the mosaic definition (#105)

## 3.0a8 (2020-08-21)

* BaseBackend is now a subclass of rio-tiler.io.base.BaseReader (add minzoom, maxzoom, bounds properties and info method)
* use `attr` to define backend classes

### Breaking changes
* `backend_options` is now used to pass options (*kwargs) to the `_read` method

## 3.0a7 (2020-07-31)

* update to rio-tiler 2.0b5

### Breaking changes
* 'value' -> 'values' in MosaicBackend.point output (#98)

## 3.0a6 (2020-07-31)

* Use environement variable to set/disable cache (#93, autho @geospatial-jeff)
* Allow Threads configuration for overview command (author @kylebarron)
* add --in-memory/--no-in-memory to control temporary files creation for `overview` function.
* allow pixel_selection method options for `overview` function.
* update to rio-tiler 2.0b4
* use new COGReader and STACReader to add .tile and .point methods directly in the backends

### Breaking changes
* backend.tile -> backend.assets_for_tile
* backend.point -> backend.assets_for_point

## 3.0a5 (2020-06-29)

* remove FTP from supported backend (#87, author @geospatial-jeff)
* add backend CRUD exceptions (#86, author @geospatial-jeff)

## 3.0a4 (2020-06-25)

* add STACBackend (#82)
* fix backends caching and switch to TTL cache (#83)

## 3.0a3 (2020-05-01)

* add Upload CLI (#74, author @kylebarron)
* fix boto3 dynamodb exception (#75)

## 3.0a2 (2020-05-01)

* Better mosaicJSON model testing and default center from bounds (#73, author @geospatial-jeff)

## 3.0a1 (2020-05-01)

This is a major version, meaning a lot of refactoring was done and may lead to breaking changes.

* add quadkey_zoom option in CLI (#41, author @kylebarron)
* use R-tree from pygeos for testing intersections (#43, author @kylebarron)

### Breaking changes
* added BackendStorage for dynamodb, s3, file and http (with @kylebarron)
* added MosaicJSON pydantic model for internal mosaicjson representation (with @kylebarron and @geospatial-jeff)

## 2.0.1 (2020-01-28)

* Bug fix, use pygeos from pypi instead of git repo

## 2.0.0 (2020-01-28) - Major refactor

* remove stack related code (lambda handler, serverless)
* switch to pygeos (#24)
* bug fixes
* add `last` pixel_method

## 1.0.0 (2019-12-13)

* add tif output
* fix overview creation
* add other Web templates

## 0.3.0 (2019-11-07)

* use aws lambda layer
* add `update_mosaic` utility function
* add `/tiles/point` endpoint to get points values from a mosaic
* add logs for mosaic creation
* add custom pixel methods
* add custom color maps

### Breaking changes
* rename `/mosaic/info/<mosaicid>` to `/mosaic/<mosaicid>/info`

## 0.2.0 (2019-09-30)

* update for lambda-proxy~=5.0 (#15)
* add `minimum_tile_cover` option for mosaic creation (#16)
* add `tile_cover_sort` option (#16)
* add verbosity for cli

## 0.1.0 (2019-09-05)

* add /create.html endpoint (#14)
* update to remotepixel/amazonlinux docker image
