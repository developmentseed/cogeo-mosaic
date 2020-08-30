# STAC Backend

The STACBackend is purely dynamic, meaning it's not used to read or write a file. This backend will POST to the input url looking for STAC items which will then be used to create the mosaicJSON.

```python
import datetime
import mercantile
from cogeo_mosaic.backends.stac import STACBackend


geojson = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [
              30.810813903808594,
              29.454247067148533
            ],
            [
              30.88600158691406,
              29.454247067148533
            ],
            [
              30.88600158691406,
              29.51879923863822
            ],
            [
              30.810813903808594,
              29.51879923863822
            ],
            [
              30.810813903808594,
              29.454247067148533
            ]
          ]
        ]
      }
    }
  ]
}


date_min="2019-01-01"
date_max="2019-12-11"

start = datetime.datetime.strptime(date_min, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
end = datetime.datetime.strptime(date_max, "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

query = {
    "collections": ["sentinel-s2-l2a-cogs"],
    "datetime": f"{start}/{end}",
    "query": {
        "eo:cloud_cover": {
            "lt": 5
        }
    },
    "intersects": geojson["features"][0]["geometry"],
    "limit": 1000,
    "fields": {
      'include': ['id', 'properties.datetime', 'properties.data_coverage'],
      'exclude': ['assets']
    }
}

with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    query,
    8,
    15,
) as mosaic:
    print(mosaic.metadata)
```

## Specification

The STACBackend rely on Spec version 1.0.0alpha.

### Paggination

The returned object from the POST requests might not represent the whole results and thus
we need to use the paggination. 

You can limit the pagination by using `max_items` or `stac_query_limit` options.

- Limit the total result to 1000 items

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    max_items=1000,
) as mosaic:
    print(mosaic.metadata)
```

- Limit the size of each POST result

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    stac_query_limit=500,
) as mosaic:
    print(mosaic.metadata)
```
Warnings: trying to run the previous example will results in fetching the whole collection.


## Tile's item

MosaicJSON tile item is defined using `accessor` option. By default the backend will try to construct or retrieve the Item url

```python
def default_stac_accessor(feature: Dict):
    """Return feature identifier."""
    link = list(filter(lambda link: link["rel"] == "self", feature["links"]))
    if link:
        return link[0]["href"]

    link = list(filter(lambda link: link["rel"] == "root", feature["links"]))
    if link:
        return os.path.join(
            link[0]["href"],
            "collections",
            feature["collection"],
            "items",
            feature["id"],
        )

    # Fall back to the item ID
    return feature["id"]
```

This default accessor function rely on the `self` or `root` link to be present.

It's let to the user to built a Mosaic Tiler which will understand the asset.

#### Custom accessor

Accessor HAVE to be a callable which take a GeoJSON feature as input. 

Here is an example of an accessor that will return the ulr for asset `B01`

```python
with STACBackend(
    "https://earth-search.aws.element84.com/v0/search",
    {},
    8,
    15,
    stac_query_limit=500,
    accessor=lambda x: x["items"]["B01"]["href"],
) as mosaic:
    print(mosaic.metadata)
```