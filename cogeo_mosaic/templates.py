"""cogeo_mosaic.templates: HTML templates."""


def index(endpoint: str, token: str = "") -> str:
    """cogeo-mosaic web page."""
    return f"""<!DOCTYPE html>
    <html>
      <head>
        <meta charset='utf-8' />
        <title>cogeo-mosaic</title>
        <meta name='viewport' content='initial-scale=1,maximum-scale=1,user-scalable=no'/>

        <script src='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.js'></script>
        <link href='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.css' rel='stylesheet'/>

        <link href="https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.min.css" rel="stylesheet">
        <script src="https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.js"></script>
        <script src='https://npmcdn.com/@turf/turf/turf.min.js'></script>

        <style>
          body {{ margin:0; padding:0; width:100%; height:100%;}}
          #map {{ position:absolute; top:0; bottom:0; width:100%; }}
          .mosaic-info {{
              z-index: 10;
              position: absolute;
              top: 5px;
              right: 0;
              padding: 5px;
              width: auto;
              height: auto;
              font-size: 18px;
              color: #000;
          }}
          .zoom-info {{
              z-index: 10;
              position: absolute;
              bottom: 17px;
              right: 0;
              padding: 5px;
              width: auto;
              height: auto;
              font-size: 16px;
              color: #000;
          }}
          .loading-map {{
              position: absolute;
              width: 100%;
              height: 100%;
              color: #FFF;
              background-color: #000;
              text-align: center;
              opacity: 0.5;
              font-size: 45px;
          }}
          .loading-map.off {{
              opacity: 0;
              -o-transition: all .5s ease;
              -webkit-transition: all .5s ease;
              -moz-transition: all .5s ease;
              -ms-transition: all .5s ease;
              transition: all ease .5s;
              visibility:hidden;
          }}
          .middle-center {{
              position: absolute;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
          }}
          .middle-center * {{
              display: block;
              padding: 5px;
          }}
        </style>
      </head>
    <body>
    <div  id='selector' class='fixed top right bottom left scroll-auto bg-darken25 z3'>
      <div class='bg-white middle-center w600 px12 py12 round'>
        <div class='txt-h5 mt6 mb6 color-black'>Enter mosaic url</div>
        <input id="mosaic" class='input wmax-full inline-block' value="" placeholder='mosaic url here'/>
        <button id="launch" class='btn bts--xs btn--stroke bg-darken25-on-hover inline-block mt12 '>Apply</button>
      </div>
    </div>
    <div id='map'>
      <div id='loader' class="loading-map z2">
        <div class="middle-center">
          <div class="round animation-spin animation--infinite animation--speed-1">
              <svg class='icon icon--l inline-block'><use xlink:href='#icon-satellite'/></svg>
          </div>
        </div>
      </div>
      <div class="mosaic-info">
        <span class='py3' style='display: block; text-align: right;' id="name"></span>
        <span class='py3' style='display: block; text-align: right;' id="min-zoom"></span>
        <span class='py3' style='display: block; text-align: right;' id="max-zoom"></span>
      </div>
      <div class="zoom-info"><span id="zoom"></span></div>
    </div>

    <script>
      mapboxgl.accessToken = '{token}'
      let style
      if (mapboxgl.accessToken !== '') {{
        style = 'mapbox://styles/mapbox/basic-v9'
      }} else {{
        style = {{ version: 8, sources: {{}}, layers: [] }}
      }}

      var map = new mapboxgl.Map({{
          container: 'map',
          style: style,
          center: [0, 0],
          zoom: 1
      }})

      map.on('zoom', function (e) {{
        const z = (map.getZoom()).toString().slice(0, 6)
        document.getElementById('zoom').textContent = z
      }})

      const addAOI = (bounds) => {{
        const geojson = {{
          'type': 'FeatureCollection',
          'features': [ turf.bboxPolygon(bounds) ]
        }}
        map.addSource('aoi', {{
          'type': 'geojson',
          'data': geojson
        }})
        map.addLayer({{
          id: 'aoi-polygon',
          type: 'line',
          source: 'aoi',
          layout: {{
            'line-cap': 'round',
            'line-join': 'round'
          }},
          paint: {{
            'line-color': '#3bb2d0',
            'line-width': 2
          }}
        }})
        return
      }}
      const addMosaic = (mosaicUrl, options) => {{
        return fetch(`{endpoint}/mosaic/info?url=${{mosaicUrl}}`)
          .then(res => {{
            if (res.ok) return res.json()
            throw new Error('Network response was not ok.')
          }})
          .then(data => {{
            document.getElementById('name').textContent = `${{data.name}}`
            document.getElementById('min-zoom').textContent = `Min Zoom: ${{data.minzoom}}`
            document.getElementById('max-zoom').textContent = `Max Zoom: ${{data.maxzoom}}`
            const tileParams = Object.keys(options).map(i => `${{i}}=${{options[i]}}`).join('&')
            let url = `{endpoint}/tiles/tilejson.json?url=${{mosaicUrl}}&tile_format=png`
            if (tileParams !== '') url += `&${{tileParams}}`
            map.addSource('raster', {{
              type: 'raster',
              url: url
            }})
            map.addLayer({{
              id: 'raster',
              type: 'raster',
              source: 'raster'
            }})
            document.getElementById('loader').classList.toggle('off')
            const bounds = data.bounds
            addAOI(bounds)
            map.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])
          }})
      }}

      document.getElementById('launch').addEventListener('click', () => {{
        addMosaic(document.getElementById('mosaic').value, {{}})
          .then(() => {{
            document.getElementById('selector').classList.toggle('none')
          }})
          .catch(err => {{
            console.warn(err)
          }})
      }})
    </script>
    </body>
    </html>"""


def index_create(endpoint: str, token: str = "") -> str:
    """cogeo-mosaic web page."""
    return f"""<!DOCTYPE html>
    <html>
      <head>
          <meta charset='utf-8' />
          <title>COG Mosaic</title>
          <meta name='viewport' content='initial-scale=1,maximum-scale=1,user-scalable=no' />
          <script src='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.js'></script>
          <link href='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.css' rel='stylesheet' />
          <link href="https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.min.css" rel="stylesheet">
          <script src="https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.js"></script>
          <script src='https://npmcdn.com/@turf/turf/turf.min.js'></script>
          <style>
              body {{ margin:0; padding:0; width:100%; height:100%;}}
              #map {{ position:absolute; top:0; bottom:0; width:100%; }}
              .loading-map {{
                  position: absolute;
                  width: 100%;
                  height: 100%;
                  color: #FFF;
                  background-color: #000;
                  text-align: center;
                  opacity: 0.5;
                  font-size: 45px;
              }}
              .loading-map.off {{
                  opacity: 0;
                  -o-transition: all .5s ease;
                  -webkit-transition: all .5s ease;
                  -moz-transition: all .5s ease;
                  -ms-transition: all .5s ease;
                  transition: all ease .5s;
                  visibility:hidden;
              }}
              .middle-center {{
                  position: absolute;
                  top: 50%;
                  left: 50%;
                  transform: translate(-50%, -50%);
              }}
              .middle-center * {{
                  display: block;
                  padding: 5px;
              }}
              #drop_zone {{
                display: block;
                position: absolute;
                background-color: rgb(255, 255, 255, 0.5);
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 100;
              }}
              #drop_zone_elem {{
                  border: 2px dashed #000;
                  -moz-border-radius: 5px;
                  -webkit-border-radius: 5px;
                  border-radius: 5px;
                  margin: 25px;
                  text-align: center;
                  font: 20pt bold;
                  color: #000;
                  display: block;
                  width: calc(100% - 50px);
                  height: calc(100% - 50px);
              }}
              #drop_zone_elem.hover {{ border: 10px dashed #333; }}
              #mosaic_id {{
                z-index: 1;
                position: absolute;
                padding: 5px;
                top: 5px;
                right: 5px;
                color: #FFF;
                font: 15pt bold;
              }}
            </style>
      </head>
      <body>
        <div id="drop_zone">
          <div id="drop_zone_elem">
            <span class='middle-center'>Drop file here</span>
          </div>
        </div>
        <div id='map'>
          <span id="mosaic_id"></span>
          <div id='loader' class="loading-map z2 off">
            <div class="middle-center">
              <div class="round animation-spin animation--infinite animation--speed-1">
                <svg class='icon icon--l inline-block'><use xlink:href='#icon-satellite'/></svg>
              </div>
            </div>
          </div>
        </div>

        <script>

    mapboxgl.accessToken = '{token}'
    let style
    if (mapboxgl.accessToken !== '') {{
      style = 'mapbox://styles/mapbox/basic-v9'
    }} else {{
      style = {{ version: 8, sources: {{}}, layers: [] }}
    }}

    var map = new mapboxgl.Map({{
        container: 'map',
        style: style,
        center: [0, 0],
        zoom: 1
    }})

    const getFootprint = (list) => {{
      return fetch('{endpoint}/mosaic/footprint', {{ mode: 'cors', method: "POST", body: JSON.stringify(list) }})
        .then(res => {{
          if (res.ok) return res.json()
          throw new Error('Network response was not ok.')
        }})
        .then(geojson => {{
          map.addSource('borders', {{
            'type': 'geojson',
            'data': geojson
          }})
          map.addLayer({{
            id: 'borders',
            type: 'line',
            source: 'borders',
            layout: {{
              'line-cap': 'round',
              'line-join': 'round'
            }},
            paint: {{
              'line-color': '#000',
              'line-width': 2
            }}
          }})
        }})
    }}

    const getMosaic = (list) => {{
      return fetch('{endpoint}/mosaic/create', {{ mode: 'cors', method: "POST", body: JSON.stringify(list)}})
        .then(res => {{
          if (res.ok) return res.json()
          throw new Error('Network response was not ok.')
        }})
        .then(tilejson => {{
          document.getElementById('mosaic_id').textContent = tilejson.name
          map.addSource('raster', {{
            type: 'raster',
            tiles: tilejson.tiles,
            tileSize: 256,
            bounds: tilejson.bounds,
            minzoom: tilejson.minzoom,
            maxzoom: tilejson.maxzoom,
          }})
          map.addLayer({{ id: 'raster', type: 'raster', source: 'raster' }})
          map.fitBounds([
            [tilejson.bounds[0], tilejson.bounds[1]],
            [tilejson.bounds[2], tilejson.bounds[3]]
          ])
        }})
    }}

    // Check for the various File API support.
    if (window.File && window.FileReader && window.FileList && window.Blob) {{
      // Great success! All the File APIs are supported.
    }} else {{
      alert('The File APIs are not fully supported in this browser.');
    }}

    const handleFileSelect = (evt) => {{
      evt.stopPropagation()
      evt.preventDefault()

      var files = evt.dataTransfer.files
      if (files.length !== 1) throw "Must drag only one file"
      var file = files[0],
      reader = new FileReader();
      reader.onload = function(event) {{
        document.getElementById('drop_zone').classList.toggle('none')
        document.getElementById('loader').classList.toggle('off')
          list = event.target.result.split(/\\n/);
          list = list.filter((e) => {{ return e !== '' }});
          Promise.all([getMosaic(list), getFootprint(list)])
            .then(() => {{
              document.getElementById('loader').classList.toggle('off')
            }})
            .catch(err => {{
              document.getElementById('drop_zone').classList.toggle('none')
              document.getElementById('loader').classList.toggle('off')
              console.warn(err)
            }})
      }};
      reader.readAsText(file);
    }}

    const handleDragOver = (evt) => {{
      evt.stopPropagation();
      evt.preventDefault();
      evt.className = 'hover';
      evt.dataTransfer.dropEffect = 'copy'; // Explicitly show this is a copy.
    }}
    const handleDragEnd = (evt) => {{
      this.className = '';
    }}

    // Setup the dnd listeners.
    var dropZone = document.getElementById('drop_zone_elem');
    dropZone.addEventListener('dragover', handleDragOver, false);
    dropZone.addEventListener('ondragend', handleDragEnd, false);
    dropZone.addEventListener('drop', handleFileSelect, false);
    </script>

    </body>
    </html>"""
