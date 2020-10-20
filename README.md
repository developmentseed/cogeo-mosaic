# cogeo-mosaic

<p align="center">
  <img src="https://user-images.githubusercontent.com/10407788/73185274-c41dc900-40eb-11ea-8b67-f79c0682c3b0.jpg" style="max-width: 800px;" alt="rio-tiler"></a>
</p>
<p align="center">
  <em>Create mosaics of Cloud Optimized GeoTIFF based on <a href='https://github.com/developmentseed/mosaicjson-spec'>mosaicJSON</a> specification.</em>
</p>
<p align="center">
  <a href="https://github.com/developmentseed/cogeo-mosaic/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/developmentseed/cogeo-mosaic/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://codecov.io/gh/developmentseed/cogeo-mosaic" target="_blank">
      <img src="https://codecov.io/gh/developmentseed/cogeo-mosaic/branch/master/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/cogeo-mosaic" target="_blank">
      <img src="https://img.shields.io/pypi/v/cogeo-mosaic?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>

  <a href="https://pypistats.org/packages/cogeo-mosaic" target="_blank">
      <img src="https://img.shields.io/pypi/dm/cogeo-mosaic.svg" alt="Downloads">
  </a>
  <a href="https://github.com/developmentseed/cogeo-mosaic/blob/master/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/developmentseed/cogeo-mosaic.svg" alt="Downloads">
  </a>
</p>

---

**Documentation**: <a href="https://developmentseed.org/cogeo-mosaic/" target="_blank">https://developmentseed.org/cogeo-mosaic/</a>

**Source Code**: <a href="https://github.com/developmentseed/cogeo-mosaic" target="_blank">https://github.com/developmentseed/cogeo-mosaic</a>

---

**Read the official announcement https://medium.com/devseed/cog-talk-part-2-mosaics-bbbf474e66df**

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


# See it in actions

- [**TiTiler**](http://github.com/developmentseed/titiler): A lightweight Cloud Optimized GeoTIFF dynamic tile server (COG, STAC and MosaicJSON).

## Contribution & Development

See [CONTRIBUTING.md](https://github.com/developmentseed/cogeo-mosaic/blob/master/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com/developmentseed/cogeo-mosaic/blob/master/LICENSE)

## Authors

Created by [Development Seed](<http://developmentseed.org>)

## Changes

See [CHANGES.md](https://github.com/developmentseed/cogeo-mosaic/blob/master/CHANGES.md).
