## API

### OpenAPI

https://08lazntuxe.execute-api.us-east-1.amazonaws.com/production/docs


### Create footprint GeoJSON
`/footprint`

- methods: GET | POST
- **body**
  - content: List of files
  - format: **json**
- returns: footprint geojson (application/json, compression: **gzip**)

Note: equivalent of running `cogeo-mosaic footprint` locally 

```bash
$ curl -X POST -F 'json=@list.json' https://{endpoint-url}/footprint`
```


### Create mosaic defintion file
`/mosaic`

- methods: GET | POST
- **body**
  - content: List of files
  - format: **json**
- returns: mosaic definition (application/json, compression: **gzip**)

Note: equivalent of running `cogeo-mosaic create` locally 

```bash
$ curl -X POST -F 'json=@list.json' https://{endpoint-url}/mosaic`
```

### TileJSON (2.1.0)
`/tilejson.json`

- methods: GET
- **url** (required): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **kwargs** (in querytring): tiler options
- returns: tijeson defintion (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/tilejson.json?url=s3://my_file.json.gz
```

```json
meta = {
    "bounds": [...],
    "center": [lon, lat, minzoom],
    "maxzoom": 22,
    "minzoom": 18,
    "name": "my_file.json.gz",
    "tilejson": "2.1.0",
    "tiles": [
        "https://{endpoint-url}/{{z}}/{{x}}/{{y}}@2x.<ext>"
    ],
}
```

### Mosaic Metadata
`/info`

- methods: GET
- **url** (in querytring): mosaic definition url
- returns: mosaic defintion info (application/json, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/info?url=s3://my_file.json.gz)
```

```json
meta = {
    "bounds": [...],            // mosaic bounds
    "center": [lon, lat, zoom], // mosaic center
    "maxzoom": 22,              // mosaic max zoom
    "minzoom": 18,              // mosaic min zoom
    "name": "my_file.json.gz",   // mosaic basename
    "quadkeys": [...],          // list of quakeys
    "layers": [...] ,           // dataset band names
}
```

### wmts
`/wmts`

- methods: GET
- **url** (in querytring): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **tile_scale** (optional, int): output tile scale (default: 1 = 256px)
- **kwargs** (in querytring): tiler options
- returns: WMTS xml (application/xml, compression: **gzip**)

```bash
$ curl https://{endpoint-url}/wmts?url=s3://my_file.json.gz)
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
                        <ows:Get xlink:href="https://o4m49i49o5.execute-api.us-east-1.amazonaws.com/production/wmts?url=http%3A%2F%2Fmymosaic.json">
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
                        <ows:Get xlink:href="https://o4m49i49o5.execute-api.us-east-1.amazonaws.com/production/wmts?url=http%3A%2F%2Fmymosaic.json">
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
                    template="https://o4m49i49o5.execute-api.us-east-1.amazonaws.com/production/{TileMatrix}/{TileCol}/{TileRow}@1x.png?url=http%3A%2F%2Fmymosaic.json"/>
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
        <ServiceMetadataURL xlink:href='https://o4m49i49o5.execute-api.us-east-1.amazonaws.com/production/wmts?url=http%3A%2F%2Fmymosaic.json'/>
    </Capabilities>
```
</details>

### Get image tiles
`/<int:z>/<int:x>/<int:y>.<ext>`

`/<int:z>/<int:x>/<int:y>@2x.<ext>`

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
$ curl https://{endpoint-url}/8/32/22.png?url=s3://my_file.json.gz&indexes=1,2,3&rescale=100,3000&color_ops=Gamma RGB 3&pixel_selection=first
```