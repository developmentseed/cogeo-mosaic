# API

## Web page

https://cogeo.xyz

`/`

`/index.html`

Visualize a mosaic-json

![https://cogeo.xyz/index.html
](https://user-images.githubusercontent.com/10407788/64351391-391b2580-cfc8-11e9-9f53-92a35c0c0500.png)


`/create.html`

Create mosaic-json and visualize

![https://cogeo.xyz/create.html](https://user-images.githubusercontent.com/10407788/64351389-37e9f880-cfc8-11e9-940a-ec8c9ec307e2.png)


## Mosaic

https://cogeo.xyz/mosaic/docs


### Create mosaic defintion file
`/mosaic/create`

- methods: GET | POST
- **body**
  - content: List of files
  - format: **json**
- returns: mosaic definition (application/json, compression: **gzip**)

Note: equivalent of running `cogeo-mosaic create` locally 

```bash
$ curl -X POST -F 'json=@list.json' https://{endpoint-url}/mosaic/create`
```


### Create footprint GeoJSON
`/mosaic/footprint`

- methods: GET | POST
- **body**
  - content: List of files
  - format: **json**
- returns: footprint geojson (application/json, compression: **gzip**)

Note: equivalent of running `cogeo-mosaic footprint` locally 

```bash
 $ curl -X POST -F 'json=@list.json' https://{endpoint-url}/mosaic/footprint
```

### Mosaic Metadata
`/mosaic/info`
- methods: GET
- **url** (in querytring): mosaic definition url
- returns: mosaic defintion info (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/mosaic/info?url=https://my-mosaic.json.gz
```

`/mosaic/<mosaicid>/info`
- methods: GET
- **mosaicid** (in path): mosaic definition id
- returns: mosaic defintion info (application/json, compression: **gzip**)


```bash
$ curl https://{endpoint-url}/mosaic/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/info
```

```json
{
    "bounds": [...],                // mosaic bounds
    "center": [lon, lat, zoom],     // mosaic center
    "maxzoom": 22,                  // mosaic max zoom
    "minzoom": 18,                  // mosaic min zoom
    "name": "s3://my_file.json.gz", // mosaic basename
    "quadkeys": [...],              // list of quakeys
    "layers": [...] ,               // dataset band names
}
```

### Mosaic GeoJSON

`/mosaic/geojson`
- methods: GET
- **url** (in querytring): mosaic definition url
- returns: mosaic-json as geojson (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/mosaic/geojson?url=s3://my_file.json.gz
```

`/mosaic/<mosaicid>/geojson`
- methods: GET
- **mosaicid** (in path): mosaic definition id
- returns: mosaic-json as geojson (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/mosaic/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/geojson
```



```json
{
    "type":"FeatureCollection",
    "features":[
        {
            "type":"Feature",
            "bbox":[...],
            "id":"Tile(x=21, y=20, z=7)",
            "geometry":{
                "type":"Polygon",
                "coordinates":[[
                    ...
                ]]
            },
            "properties":{
                "title":"XYZ tile Tile(x=21, y=20, z=7)",
                "files":["s3://ds-satellite/cogs/ABoVE_LandCover_1984_2014/ABoVE_LandCover_Bh15v03_cog.tif"]
            }
        }
        ...
    ]
}
```

## Tiles

https://cogeo.xyz/tiles/docs


### TileJSON (2.1.0)
`/tiles/tilejson.json`

- methods: GET
- **url** (required): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **kwargs** (in querytring): tiler options
- returns: tileJSON defintion (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tiles/tilejson.json?url=s3://my_file.json.gz
```

`/tiles/<mosaicid>/tilejson.json`

- methods: GET
- **mosaicid** (in path): mosaic definition id
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **kwargs** (in querytring): tiler options
- returns: tileJSON defintion (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tiles/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/tilejson.json
```

```json
{
    "bounds": [...],
    "center": [lon, lat, minzoom],
    "maxzoom": 22,
    "minzoom": 18,
    "name": "s3://my_file.json.gz",
    "tilejson": "2.1.0",
    "tiles": [
        "https://{endpoint-url}/tiles/{{z}}/{{x}}/{{y}}@2x.<ext>"
    ],
}
```

### wmts
`/tiles/wmts`

- methods: GET
- **url** (in querytring): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **title** (optional, str): layer name (default: "Cloud Optimizied GeoTIFF Mosaic")
- **kwargs** (in querytring): tiler options
- returns: WMTS xml (application/xml, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tiles/wmts?url=s3://my_file.json.gz)
```

`/tiles/<mosaicid>/wmts`

- methods: GET
- **mosaicid** (in path): mosaic definition id
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **title** (optional, str): layer name (default: "Cloud Optimizied GeoTIFF Mosaic")
- **kwargs** (in querytring): tiler options
- returns: WMTS xml (application/xml, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tiles/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/wmts)
```
<details>

```xml
<Capabilities
        xmlns="http://www.opengis.net/wmts/1.0"
        xmlns:ows="http://www.opengis.net/ows/1.1"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:gml="http://www.opengis.net/gml"
        xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
        version="1.0.0">
       <ows:ServiceIdentification>
            <ows:Title>Cloud Optimizied GeoTIFF Mosaic</ows:Title>
            <ows:ServiceType>OGC WMTS</ows:ServiceType>
            <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        </ows:ServiceIdentification>
        <ows:OperationsMetadata>
            <ows:Operation name="GetCapabilities">
                <ows:DCP>
                    <ows:HTTP>
                        <ows:Get xlink:href="https://{endpoint-url}/tiles/wmts?url=http%3A%2F%2Fmymosaic.json">
                            <ows:Constraint name="GetEncoding">
                                <ows:AllowedValues>
                                    <ows:Value>RESTful</ows:Value>
                                </ows:AllowedValues>
                            </ows:Constraint>
                        </ows:Get>
                    </ows:HTTP>
                </ows:DCP>
            </ows:Operation>
            <ows:Operation name="GetTile">
                <ows:DCP>
                    <ows:HTTP>
                        <ows:Get xlink:href="https://{endpoint-url}/tiles/wmts?url=http%3A%2F%2Fmymosaic.json">
                            <ows:Constraint name="GetEncoding">
                                <ows:AllowedValues>
                                    <ows:Value>RESTful</ows:Value>
                                </ows:AllowedValues>
                            </ows:Constraint>
                        </ows:Get>
                    </ows:HTTP>
                </ows:DCP>
            </ows:Operation>
        </ows:OperationsMetadata>
        <Contents>
            <Layer>
                <ows:Title>Cloud Optimizied GeoTIFF Mosaic</ows:Title>
                <ows:Identifier>mymosaic.json</ows:Identifier>
                <ows:Abstract>cogeo-mosaic</ows:Abstract>
                <ows:WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
                    <ows:LowerCorner>-75.98703377403767 44.93504283303786</ows:LowerCorner>
                    <ows:UpperCorner>-71.337604724099 47.096855991923235</ows:UpperCorner>
                </ows:WGS84BoundingBox>
                <Style isDefault="true">
                    <ows:Identifier>default</ows:Identifier>
                </Style>
                <Format>image/png</Format>
                <TileMatrixSetLink>
                    <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                </TileMatrixSetLink>
                <ResourceURL
                    format="image/png"
                    resourceType="tile"
                    template="https://{endpoint-url}/tiles/{TileMatrix}/{TileCol}/{TileRow}@1x.png?url=http%3A%2F%2Fmymosaic.json"/>
            </Layer>
            <TileMatrixSet>
                <ows:Title>GoogleMapsCompatible</ows:Title>
                <ows:Abstract>GoogleMapsCompatible EPSG:3857</ows:Abstract>
                <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
                <ows:SupportedCRS>urn:ogc:def:crs:EPSG::3857</ows:SupportedCRS>
                <TileMatrix>
            <ows:Identifier>7</ows:Identifier>
            <ScaleDenominator>4367830.187724375</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>128</MatrixWidth>
            <MatrixHeight>128</MatrixHeight>
        </TileMatrix>
<TileMatrix>
            <ows:Identifier>8</ows:Identifier>
            <ScaleDenominator>2183915.0938621876</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>256</MatrixWidth>
            <MatrixHeight>256</MatrixHeight>
        </TileMatrix>
<TileMatrix>
            <ows:Identifier>9</ows:Identifier>
            <ScaleDenominator>1091957.5469310938</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>256</TileWidth>
            <TileHeight>256</TileHeight>
            <MatrixWidth>512</MatrixWidth>
            <MatrixHeight>512</MatrixHeight>
        </TileMatrix>
            </TileMatrixSet>
        </Contents>
        <ServiceMetadataURL xlink:href='https://{endpoint-url}/tiles/wmts?url=http%3A%2F%2Fmymosaic.json'/>
    </Capabilities>
```
</details>

### Get image tiles
`/tiles/<int:z>/<int:x>/<int:y>.<ext>`

`/tiles/<int:z>/<int:x>/<int:y>@2x.<ext>`

- methods: GET
- **z**: Mercator tile zoom value
- **x**: Mercator tile x value
- **y**: Mercator tile y value
- **scale**: Tile scale (default: 1)
- **ext**: Output tile format (e.g `jpg`)
- **url** (required): mosaic definition url
- **indexes** (optional, str): dataset band indexes (default: None)
- **rescale** (optional, str): min/max for data rescaling (default: None)
- **color_ops** (optional, str): rio-color formula (default: None)
- **color_map** (optional, str): rio-tiler colormap (default: None)
- **pixel_selection** (optional, str): mosaic pixel selection (default: `first`)
- **resampling_method** (optional, str): tiler resampling method (default: `nearest`)
- compression: **gzip**
- returns: image body (image/jpeg)

```bash
$ curl https://{endpoint-url}/tiles/8/32/22.png?url=s3://my_file.json.gz&indexes=1,2,3&rescale=100,3000&color_ops=Gamma RGB 3&pixel_selection=first
```

`/tiles/<mosaicid>/<int:z>/<int:x>/<int:y>.<ext>`

`/tiles/<mosaicid>/<int:z>/<int:x>/<int:y>@2x.<ext>`

- methods: GET
- **mosaicid** (in path): mosaic definition id
- **z**: Mercator tile zoom value
- **x**: Mercator tile x value
- **y**: Mercator tile y value
- **scale**: Tile scale (default: 1)
- **ext**: Output tile format (e.g `jpg`)
- **indexes** (optional, str): dataset band indexes (default: None)
- **rescale** (optional, str): min/max for data rescaling (default: None)
- **color_ops** (optional, str): rio-color formula (default: None)
- **color_map** (optional, str): rio-tiler colormap (default: None)
- **pixel_selection** (optional, str): mosaic pixel selection (default: `first`)
- **resampling_method** (optional, str): tiler resampling method (default: `nearest`)
- compression: **gzip**
- returns: image body (image/jpeg)

```bash
$ curl https://{endpoint-url}/tiles/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/8/32/22.png?indexes=1,2,3&rescale=100,3000&color_ops=Gamma RGB 3&pixel_selection=first
```

### Get Vector tiles

`/tiles/<int:z>/<int:x>/<int:y>.<pbf>`

- methods: GET
- **z**: Mercator tile zoom value
- **x**: Mercator tile x value
- **y**: Mercator tile y value
- **ext**: Output tile format (e.g `jpg`)
- **url** (required): mosaic definition url
- **tile_size**: (optional, int) Tile size (default: 256)
- **pixel_selection** (optional, str): mosaic pixel selection (default: `first`)
- **feature_type** (optional, str): feature type (default: `point`)
- **resampling_method** (optional, str): tiler resampling method (default: `nearest`)
- compression: **gzip**
- returns: tile body (application/x-protobuf)

```bash
$ curl https://{endpoint-url}/tiles/8/32/22.pbf?url=s3://my_file.json.gz&pixel_selection=first
```

`/tiles/<mosaicid>/<int:z>/<int:x>/<int:y>.<pbf>`

- methods: GET
- **mosaicid** (in path): mosaic definition id
- **z**: Mercator tile zoom value
- **x**: Mercator tile x value
- **y**: Mercator tile y value
- **tile_size**: (optional, int) Tile size (default: 256)
- **pixel_selection** (optional, str): mosaic pixel selection (default: `first`)
- **feature_type** (optional, str): feature type (default: `point`)
- **resampling_method** (optional, str): tiler resampling method (default: `nearest`)
- compression: **gzip**
- returns: tile body (application/x-protobuf)

```bash
$ curl https://{endpoint-url}/tiles/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/8/32/22.pbf?pixel_selection=first
```


### Get Point Value

`/tiles/point`

- methods: GET
- **lng** (required, float): longitude
- **lat** (required, float): lattitude
- **url** (required): mosaic definition url
- compression: **gzip**
- returns: json(application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tiles/point?url=s3://my_file.json.gz&lng=10&lat=-10
```

`/tiles/<mosaicid>/point`

- methods: GET
- **mosaicid** (in path): mosaic definition id
- **lng** (required, float): longitude
- **lat** (required, float): lattitude
- compression: **gzip**
- returns: tile body (application/x-protobuf)

```bash
$ curl https://{endpoint-url}/tiles/0505ad234b5fb97df134001709b8a42eddce5d
03b200eb8f7f4540d6/point?lng=10&lat=-10
```

