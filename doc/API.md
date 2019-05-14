## API


### Create mosaic defintion file
`/create_mosaic`

- methods: GET | POST
- **body**
  - content: List of files
  - format: json
- returns: mosaic definition (application/json)

Note: equivalent of running `cog-mosaic create` locally 

```bash
$ curl -X POST -F 'json=@list.json' https://{endpoint-url}/create_mosaic`
```

### TileJSON (2.1.0)
`/mosaic/tilejson.json`

- methods: GET
- **url** (required): mosaic definition url
- **tile_format** (optional, str): output tile format (default: "png")
- **kwargs** (in querytring): tiler independant options
- returns: tijeson defintion (application/json)

```bash
$ curl https://{endpoint-url}/mosaic/tilejson.json?url=s3://my_file.json.gz
```

### Mosaic Metadata
`/mosaic/info`

- methods: GET
- **url** (in querytring): mosaic definition url
- returns: mosaic defintion info (application/json)

```bash
$ curl https://{endpoint-url}/mosaic/info?url=s3://my_file.json.gz)
```

```json
meta = {
    "bounds": [...],          // mosaic bounds
    "center": [lon, lat],     // mosaic center
    "maxzoom": 22,            // mosaic max zoom
    "minzoom": 18,            // mosaic min zoom
    "name": "mosaic.json.gz", // mosaic basename
    "quadkeys": [...],        // list of quakeys
    "layers": [...] ,         // dataset band names
}
```

### Get image tiles
`/mosaic/<int:z>/<int:x>/<int:y>.<ext>`
`/mosaic/<int:z>/<int:x>/<int:y>@2x.<ext>`

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
- **pixel_selection** (optional, str): mosaic pixel selection (default: `scene`)
- **resampling_method** (optional, str): tiler resampling method (default: `nearest`)
- compression: **gzip**
- returns: image body (image/jpeg)

```bash
$ curl https://{endpoint-url}/mosaic/8/32/22.png?url=s3://my_file.json.gz&indexes=1,2,3&rescale=100,3000&color_ops=Gamma RGB 3&pixel_selection=darkest
```