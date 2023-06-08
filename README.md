# cogeo-mosaic

<p align="center">
  <img src="https://user-images.githubusercontent.com/10407788/73185274-c41dc900-40eb-11ea-8b67-f79c0682c3b0.jpg" style="max-width: 800px;" alt="rio-tiler"></a>
</p>
<p align="center">
  <em>Create mosaics of Cloud Optimized GeoTIFF based on the <a href='https://github.com/developmentseed/mosaicjson-spec'>mosaicJSON</a> specification.</em>
</p>
<p align="center">
  <a href="https://github.com/developmentseed/cogeo-mosaic/actions?query=workflow%3ACI" target="_blank">
      <img src="https://github.com/developmentseed/cogeo-mosaic/workflows/CI/badge.svg" alt="Test">
  </a>
  <a href="https://codecov.io/gh/developmentseed/cogeo-mosaic" target="_blank">
      <img src="https://codecov.io/gh/developmentseed/cogeo-mosaic/branch/main/graph/badge.svg" alt="Coverage">
  </a>
  <a href="https://pypi.org/project/cogeo-mosaic" target="_blank">
      <img src="https://img.shields.io/pypi/v/cogeo-mosaic?color=%2334D058&label=pypi%20package" alt="Package version">
  </a>

  <a href="https://pypistats.org/packages/cogeo-mosaic" target="_blank">
      <img src="https://img.shields.io/pypi/dm/cogeo-mosaic.svg" alt="Downloads">
  </a>
  <a href="https://github.com/developmentseed/cogeo-mosaic/blob/main/LICENSE" target="_blank">
      <img src="https://img.shields.io/github/license/developmentseed/cogeo-mosaic.svg" alt="Downloads">
  </a>
</p>

---

**Documentation**: <a href="https://developmentseed.org/cogeo-mosaic/" target="_blank">https://developmentseed.org/cogeo-mosaic/</a>

**Source Code**: <a href="https://github.com/developmentseed/cogeo-mosaic" target="_blank">https://github.com/developmentseed/cogeo-mosaic</a>

---

**Read the official announcement https://medium.com/devseed/cog-talk-part-2-mosaics-bbbf474e66df**

## Install
```bash
python -m pip install pip -U
python -m pip install cogeo-mosaic --pre

# Or from source

python -m pip install git+http://github.com/developmentseed/cogeo-mosaic
```

**Notes**:

- Starting with version 5.0, pygeos has been replaced by shapely and thus makes `libgeos` a requirement.
Shapely wheels should be available for most environment, if not, you'll need to have libgeos installed.

## See it in action

- [**TiTiler**](http://github.com/developmentseed/titiler): A lightweight Cloud Optimized GeoTIFF dynamic tile server (COG, STAC and MosaicJSON).

## Contribution & Development

See [CONTRIBUTING.md](https://github.com/developmentseed/cogeo-mosaic/blob/master/CONTRIBUTING.md)

## License

See [LICENSE](https://github.com/developmentseed/cogeo-mosaic/blob/master/LICENSE)

## Authors

Created by [Development Seed](<http://developmentseed.org>)

See [contributors](https://github.com/developmentseed/cogeo-mosaic/graphs/contributors) for a listing of individual contributors.
