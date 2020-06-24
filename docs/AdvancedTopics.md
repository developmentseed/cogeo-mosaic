# Advanced Topics

## Custom mosaic creation

`MosaicJSON._create_mosaic()` method is the low level method that creates mosaicjson document. It has multiple required arguments and options with default values which more advanced users would change.


```python
# cogeo_mosaic.mosaic.MosaicJSON._create_mosaic
def _create_mosaic(
    cls,
    features: Sequence[Dict],
    minzoom: int,
    maxzoom: int,
    quadkey_zoom: Optional[int] = None,
    accessor: Callable[[Dict], str] = default_accessor,
    asset_filter: Callable = default_filter,
    version: str = "0.0.2",
    quiet: bool = True,
    **kwargs,
):
```

#### Custom Accessor

MosaicJSON `create` method takes a list of GeoJSON features has input, those can be the output of [cogeo_mosaic.utils.get_footprints](https://github.com/developmentseed/cogeo-mosaic/blob/9e8cfd0d65706faaac3e3d785974f890f3b6b180/cogeo_mosaic/utils.py#L80-L111) or can be provided by the user (e.g STAC items). MosaicJSON defines it's tile assets as a `MUST be arrays of strings (url or sceneid) pointing to a COG`. To access those values, `_create_mosaic` needs to know which **property** to read from the GeoJSON feature.

The **accessor** option is here to enable user to pass their own accessor model. By default, `_create_mosaic` expect features from `get_footprints` and thus COG path stored in `feature["properties"]["path"]`.

Example:

```python
from cogeo_mosaic.mosaic import MosaicJSON

features = [{"url": "1.tif", "geometry": {...}}, {"url": "2.tif", "geometry": {...}}]
minzoom = 1
maxzoom = 6

custom_id = lambda feature: feature["url"]

# 'from_features' will pass all args and kwargs to '_create_mosaic'
mosaicjson = MosaicJSON.from_features(
    features,
    minzoom,
    maxzoom,
    accessor=custom_id,
)
```

#### Custom asset filtering

On **mosaicjson** creation ones would want to perform more advanced assets filtering or sorting. To enable this, users can define their own `filter` method and pass it using the `asset_filter` options.

**!!!** In the current implementation, `asset_filter` method **have to** allow at least 3 arguments: 
- **tile** - mercantile.Tile: Mercantile tile
- **dataset** - Sequence[Dict]: GeoJSON Feature list intersecting with the `tile`
- **geoms** - Sequence[polygons]: Geos Polygon list for the features

Example:

```python
import datetime
from cogeo_mosaic.mosaic import MosaicJSON, default_filter

features = [{"url": "20190101.tif", "geometry": {...}}, {"url": "20190102.tif", "geometry": {...}}]
minzoom = 1
maxzoom = 6

def custom_filter(**args, **kwargs):
    """Default filter + sort."""
    dataset = default_filter(**args, **kwargs)
    return sorted(
        dataset,
        key=lambda x: datetime.datetime.strptime(x["url"].split(".")[0], "%Y%m%d")
    )

mosaicjson = MosaicJSON.from_features(
    features,
    minzoom,
    maxzoom,
    asset_filter=custom_filter,
)
```

## Custom mosaic update

Update method is **backend specific** because you don't write a mosaicjson document in the same way in AWS S3 and in AWS DynamoDB.

The **main** method is defined in [cogeo_mosaic.backends.base.BaseBackend](https://github.com/developmentseed/cogeo-mosaic/blob/master/cogeo_mosaic/backends/base.py).

On update, here is what is happening: 
1. create mosaic with the new dataset
2. loop through the new `quadkeys` and edit `old` mosaic assets
3. update bounds, center and version of the updated mosaic
4. write the mosaic

```python
# cogeo_mosaic.backends.base.BaseBackend
def update(
    self,
    features: Sequence[Dict],
    add_first: bool = True,
    quiet: bool = False,
    **kwargs,
):
    """Update existing MosaicJSON on backend."""
    # Create mosaic with the new features
    new_mosaic = self.mosaic_def.from_features(
        features,
        self.mosaic_def.minzoom,
        self.mosaic_def.maxzoom,
        quadkey_zoom=self.quadkey_zoom,
        quiet=quiet,
        **kwargs,
    )

    # Loop through the new `quadkeys` and edit `old` mosaic assets
    for quadkey, new_assets in new_mosaic.tiles.items():
        tile = mercantile.quadkey_to_tile(quadkey)
        assets = self.tile(*tile)
        assets = [*new_assets, *assets] if add_first else [*assets, *new_assets]

        # [PLACEHOLDER] add custom sorting algorithm (e.g based on path name)
        self.mosaic_def.tiles[quadkey] = assets

    # Update bounds, center and version of the updated mosaic
    bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)
    self.mosaic_def._increase_version() # Increate mosaicjson document version
    self.mosaic_def.bounds = bounds
    self.mosaic_def.center = (
        (bounds[0] + bounds[2]) / 2,
        (bounds[1] + bounds[3]) / 2,
        self.mosaic_def.minzoom,
    )

    # Write the mosaic
    if self.path:
        self.write()

    return
```

Sometime you'll will want to do more advanced filtering/sorting with the newly dataset stack (e.g keep a max number of COG). For this you'll need to create custom backend:

```python
from cogeo_mosaic.backends.s3 import S3Backend

class CustomS3Backend(S3Backend):

    _backend_name = "Custom AWS S3"

    def update(
        self,
        features: Sequence[Dict],
        quiet: bool = False,
        max_image: int = 5,
        **kwargs,
    ):
        """Update existing MosaicJSON on backend."""
        new_mosaic = self.mosaic_def.from_features(
            features,
            self.mosaic_def.minzoom,
            self.mosaic_def.maxzoom,
            quadkey_zoom=self.quadkey_zoom,
            quiet=quiet,
            **kwargs,
        )

        for quadkey, new_assets in new_mosaic.tiles.items():
            tile = mercantile.quadkey_to_tile(quadkey)
            assets = self.tile(*tile)
            assets = [*new_assets, *assets]

            self.mosaic_def.tiles[quadkey] = assets[:maximum_items_per_tile]

        bounds = bbox_union(new_mosaic.bounds, self.mosaic_def.bounds)
        self.mosaic_def._increase_version() # Increate mosaicjson document version
        self.mosaic_def.bounds = bounds
        self.mosaic_def.center = (
            (bounds[0] + bounds[2]) / 2,
            (bounds[1] + bounds[3]) / 2,
            self.mosaic_def.minzoom,
        )

        self.write()

        return
```