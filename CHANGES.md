# Release Notes

## 3.0.0-alpha.13 (2020-10-13)

* add TMS in BaseBackend to align with rio-tiler BaseBackend.

## 3.0.0-alpha.12 (2020-10-07)

* remove pkg_resources (https://github.com/pypa/setuptools/issues/510)
* raise error when `minimum_tile_cover` is > 1 (https://github.com/developmentseed/cogeo-mosaic/issues/117)
* fix wrong indices sorting in default_filter (https://github.com/developmentseed/cogeo-mosaic/issues/118)

Note: We changed the versioning scheme to {major}.{minor}.{path}-{pre}{prenum}

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
