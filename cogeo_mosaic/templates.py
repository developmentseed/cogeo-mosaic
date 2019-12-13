"""cogeo_mosaic.templates: HTML templates."""


def index(endpoint: str, token: str = "") -> str:
    """cogeo-mosaic web page."""
    return f"""<!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8' />
        <title>Cogeo-Mosaic Viewer</title>
        <meta name='viewport' content='initial-scale=1,maximum-scale=1,user-scalable=no' />

        <script src='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.js'></script>
        <link href='https://api.tiles.mapbox.com/mapbox-gl-js/v1.0.0/mapbox-gl.css' rel='stylesheet' />

        <link href='https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.min.css' rel='stylesheet'>
        <script src='https://api.mapbox.com/mapbox-assembly/v0.23.2/assembly.js'></script>

        <script src='https://npmcdn.com/@turf/turf/turf.min.js'></script>

        <style>
            body {{ margin:0; padding:0; width:100%; height:100%; }}
            #map {{ position:absolute; top:0; bottom:0; width:100%; }}

            .zoom-info {{
                z-index: 10;
                position: absolute;
                bottom: 17px;
                right: 0;
                padding: 5px;
                width: auto;
                height: auto;
                font-size: 12px;
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
            .loading-map.off{{
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

            #menu {{
                left: 0;
                top: 0;
                -o-transition: all .5s ease;
                -webkit-transition: all .5s ease;
                -moz-transition: all .5s ease;
                -ms-transition: all .5s ease;
                transition: all ease .5s;
            }}

            #menu.off {{
                left: -360px;
                -o-transition: all .5s ease;
                -webkit-transition: all .5s ease;
                -moz-transition: all .5s ease;
                -ms-transition: all .5s ease;
                transition: all ease .5s;
            }}
            #toolbar {{
                height: 35px;
            }}

            #toolbar li {{
                display: block;
                color: #fff;
                background-color: #556671;
                font-weight: 700;
                font-size: 12px;
                padding: 5px;
                height: 100%;
                width: 100%;
                text-transform: uppercase;
                text-align: center;
                text-decoration: none;
                outline: 0;
                cursor: pointer;
                -webkit-touch-callout: none;
                -webkit-user-select: none;
                    -moz-user-select: none;
                    -ms-user-select: none;
                        user-select: none;
            }}

            #toolbar li svg {{
                font-size: 25px;
                line-height: 25px;
                padding-bottom: 0;
            }}

            #toolbar li:hover {{
                background-color: #28333b;
            }}

            #toolbar li.active {{
                color: #000;
                background-color: #fff;
            }}

            #toolbar li.disabled {{
                pointer-events:none;
                opacity:0.4;
            }}

            #menu-content section {{
                display: none;
            }}

            #menu-content section.active {{
                display: inherit;
            }}

            #hide-arrow {{
                -o-transition: all .5s ease;
                -webkit-transition: all .5s ease;
                -moz-transition: all .5s ease;
                -ms-transition: all .5s ease;
                transition: all ease .5s;
            }}

            #hide-arrow.off {{
                transform: rotate(-180deg);
            }}

            #btn-hide {{
                position: absolute;
                top: 0;
                height: 35px;
                font-size: 35px;
                line-height: 35px;
                vertical-align: middle;
                right: -35px;
                color: #28333b;
                background-color: #fff;
            }}

            #btn-hide:hover {{
                color: #fff;
                background-color: #28333b;
                cursor: pointer;
            }}

            .line-red {{
                fill: none;
                stroke: red;
                stroke-width: 1.5px;
            }}
            .line-green {{
                fill: none;
                stroke: green;
                stroke-width: 1.5px;
            }}
            .line-blue {{
                fill: none;
                stroke: blue;
                stroke-width: 1.5px;
            }}

            @media(max-width: 767px) {{

                #menu.off {{
                left: -240px;
                -o-transition: all .5s ease;
                -webkit-transition: all .5s ease;
                -moz-transition: all .5s ease;
                -ms-transition: all .5s ease;
                transition: all ease .5s;
                }}

                .mapboxgl-ctrl-attrib {{
                    font-size: 10px;
                }}
            }}

        </style>
    </head>
    <body>

    <div  id='selector' class='fixed top right bottom left scroll-auto bg-darken25 z3'>
        <div class='bg-white middle-center w600-ml w300 px12 py12 round'>
            <div class='txt-h5 px0 mt6 mb6 color-black'>Enter mosaic url</div>
            <input id="mosaic" class='input wmax-full inline-block' value="" placeholder='mosaic url here'/>
            <button id="launch" class='btn bts--xs btn--stroke bg-darken25-on-hover inline-block mt6 px12'>Apply</button>
        </div>
    </div>

    <div id='menu' class='flex-child w240 w360-ml absolute bg-white z2 off'>
        <ul id='toolbar' class='grid'>
            <li id='3b' class="col col--4 active" title="rgb" onclick="switchPane(this)">
                <svg class='icon icon--l inline-block'><use xlink:href='#icon-menu'/></svg>
            </li>
            <li id='1b' class="col col--4" title="band" onclick="switchPane(this)">
                <svg class='icon icon--l inline-block'><use xlink:href='#icon-minus'/></svg>
            </li>
        </ul>

        <div id='menu-content' class='relative'>
            <!-- RGB Selection -->
            <section id='3b-section' class='px12 pt12 pb6 active'>
                <div class='txt-h5 mb6 color-black'><svg class='icon icon--l inline-block'><use xlink:href='#icon-layers'/></svg> RGB</div>
                <div id='rgb-buttons' class='align-center px6 py6'>
                <div class='select-container'>
                    <select id='r-selector' class='select select--s select--stroke wmax-full color-red'></select>
                    <div class='select-arrow color-black'></div>
                </div>

                <div class='select-container'>
                    <select id='g-selector' class='select select--s select--stroke wmax-full color-green'></select>
                    <div class='select-arrow color-black'></div>
                </div>

                <div class='select-container'>
                    <select id='b-selector' class='select select--s select--stroke wmax-full color-blue'></select>
                    <div class='select-arrow color-black'></div>
                </div>
                </div>
            </section>

            <!-- 1 Band Selection -->
            <section id='1b-section' class='px12 pt12 pb6'>
                <div class='txt-h5 mb6 color-black'>
                    <svg class='icon icon--l inline-block'><use xlink:href='#icon-layers'/></svg> Layers
                </div>
                <div class='select-container wmax-full'>
                    <select id='layer-selector' class='select select--s select--stroke wmax-full color-black'></select>
                    <div class='select-arrow color-black'></div>
                </div>

                <div class='txt-h5 mt6 mb6 color-black'>
                    <svg class='icon icon--l inline-block'><use xlink:href='#icon-layers'/></svg> Viz
                </div>
                <div id='viz-selector' class='toggle-group bg-gray-faint mt6 mb6' style="line-height: 0">
                    <label class='toggle-container'>
                        <input value="raster" checked="checked" name='toggle-viz' type='radio' />
                        <div title='Raster Viz' class='toggle color-gray-dark-on-hover'><svg class='icon icon--l inline-block w18 h18'><use xlink:href='#icon-raster'/></svg></div>
                    </label>
                    <label class='toggle-container'>
                        <input value="point" name='toggle-viz' type='radio' />
                        <div title='Point Viz' class='toggle color-gray-dark-on-hover'><svg class='icon icon--l inline-block w18 h18'><use xlink:href='#icon-circle'/></svg></div>
                    </label>
                    <label class='toggle-container'>
                        <input value="polygon" name='toggle-viz' type='radio' />
                        <div title='3D Viz' class='toggle color-gray-dark-on-hover'><svg class='icon icon--l inline-block w18 h18'><use xlink:href='#icon-extrusion'/></div>
                    </label>
                </div>

                <!-- Color Map -->
                <div id='colormap-section'>
                    <div class='txt-h5 mb6 color-black'><svg class='icon icon--l inline-block'><use xlink:href='#icon-palette'/></svg> Color Map</div>
                    <div class='select-container wmax-full'>
                        <select id='colormap-selector' class='select select--s select--stroke wmax-full color-black'>
                        <option value='b&w'>Black and White</option>
                        <option value="cfastie">CFastie</option>
                        <option value="rplumbo">RPlumbo</option>
                        <option value="schwarzwald">Schwarzwald (elevation)</option>
                        <option value="viridis">Viridis</option>
                        <option value="rdbu_r">Blue-Red</option>
                        <option value="bugn">Blue-Green</option>
                        <option value="ylgn">Yellow-Green</option>
                        <option value="magma">Magma</option>
                        <option value="gist_earth">Earth</option>
                        <option value="ocean">Ocean</option>
                        <option value="terrain">Terrain</option>                    </select>
                        <div class='select-arrow color-black'></div>
                    </div>
                </div>

                <!-- V Exag -->
                <div id='extrusion-section' class='none'>
                    <div class='txt-h5 mt6 mb6 color-black'>Vercital Exageration</div>
                    <div class='px6 py6'>
                        <input id="ex-value" class='input input--s wmax60 inline-block align-center color-black' value='1' />
                        <button id="updateExag" class='btn bts--xs btn--stroke bg-darken25-on-hover inline-block txt-s color-black ml12'>Apply</button>
                    </div>
                </div>

                <!-- Points per tiles-->
                <div id='vt-size-section' class='none'>
                    <div class='txt-h5 mt6 mb6 color-black'>Tile size</div>
                    <div id='vt-size-selector' class='toggle-group bg-gray-faint mt6 mb6' style="line-height: 0">
                        <label class='toggle-container'>
                            <input value="64" name='toggle-vt-size' type='radio' />
                            <div title='64px' class='toggle color-gray-dark-on-hover'>64px</div>
                        </label>
                        <label class='toggle-container'>
                            <input value="128" checked="checked" name='toggle-vt-size' type='radio' />
                            <div title='128'class='toggle color-gray-dark-on-hover'>128px</div>
                        </label>
                        <label class='toggle-container'>
                            <input value="256" name='toggle-vt-size' type='radio' />
                            <div title='256' class='toggle color-gray-dark-on-hover'>256px</div>
                        </label>
                    </div>
                </div>
            </section>

            <!-- Histogram Min/Max -->
            <div id='rescale-section' class='px12 pt12 none'>
                <div class='txt-h5 mt6 mb6 color-black'>Histogram Min/Max</div>
                <div class='px6 py6'>
                    <input id="min-value" class='input input--s wmax60 inline-block align-center color-black' value='0' />
                    <input id="max-value" class='input input--s wmax60 inline-block align-center color-black' value='1000' />
                    <button id="updateRescale" class='btn bts--xs btn--stroke bg-darken25-on-hover inline-block txt-s color-black ml12'>Apply</button>
                </div>
            </div>
            <section id='info' class="px12 py6 active">
                <div class='txt-h5 mb6 color-black'>Info</div>
                <div class="txt-xs"></div>

                <ul class="py6">
                    <li>- MinZoom: <span id="minzoom"></span></li>
                    <li>- MaxZoom: <span id="maxzoom"></span></li>
                    <li>- Datatype: <span id="dtype"></span></li>
                </ul>
            </section>
        </div>


        <button id='btn-hide'><svg id='hide-arrow' class='icon'><use xlink:href='#icon-arrow-right'/></svg></button>
    </div>

    <div id='map'>
        <div id='loader' class="loading-map z1">
        <div class="middle-center">
            <div class="round animation-spin animation--infinite animation--speed-1">
            <svg class='icon icon--l inline-block'><use xlink:href='#icon-satellite'/></svg>
            </div>
        </div>
        </div>
        <div class="zoom-info"><span id="zoom"></span></div>
    </div>

    <script>
    var scope = {{ metadata: {{}}}}

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

    const set1bViz = () => {{
        const vizType = document.getElementById('viz-selector').querySelector("input[name='toggle-viz']:checked").value
        let vt_size
        switch (vizType) {{
            case 'raster':
                params = {{tile_format: 'png', tile_scale: 1, url: scope.metadata.name}}
                const active_layer = document.getElementById('layer-selector')[document.getElementById('layer-selector').selectedIndex]
                indexes = active_layer.getAttribute('data-indexes')
                params.indexes = indexes

                if (scope.metadata.dtype !== "uint8") {{
                    const minV = parseFloat(document.getElementById('min-value').value)
                    const maxV = parseFloat(document.getElementById('max-value').value)
                    params.rescale =  `${{minV}},${{maxV}}`
                }}

                const cmap = document.getElementById('colormap-selector')[document.getElementById('colormap-selector').selectedIndex]
                if (cmap.value !== 'b&w') params.color_map = cmap.value

                const url_params = Object.keys(params).map(i => `${{i}}=${{params[i]}}`).join('&')
                let url = `{endpoint}/tiles/tilejson.json?${{url_params}}`

                map.addSource('raster', {{ type: 'raster', url: url , tileSize: 256}})
                addLayer(vizType)
                break

            case 'point':
                vt_size = document.getElementById('vt-size-selector').querySelector("input[name='toggle-vt-size']:checked").value
                map.addSource('mvt', {{
                    type: 'vector',
                    url: `{endpoint}/tiles/tilejson.json?tile_format=pbf&feature_type=point&tile_size=${{vt_size}}&url=${{scope.metadata.name}}`
                }})
                addLayer(vizType)
                break

            case 'polygon':
                vt_size = document.getElementById('vt-size-selector').querySelector("input[name='toggle-vt-size']:checked").value
                map.addSource('mvt', {{
                    type: 'vector',
                    url: `{endpoint}/tiles/tilejson.json?tile_format=pbf&feature_type=polygon&tile_size=${{vt_size}}&url=${{scope.metadata.name}}`
                }})
                addLayer(vizType)
                break

            default:
                throw new Error(`Invalid ${{vizType}}`)
        }}
    }}

    const set3bViz = () => {{
        const r = document.getElementById('r-selector')[document.getElementById('r-selector').selectedIndex].getAttribute('data-indexes')
        const g = document.getElementById('g-selector')[document.getElementById('g-selector').selectedIndex].getAttribute('data-indexes')
        const b = document.getElementById('b-selector')[document.getElementById('b-selector').selectedIndex].getAttribute('data-indexes')

        params = {{
            tile_format: 'png',
            tile_scale: 1,
            indexes: `${{r}},${{g}},${{b}}`,
            url: scope.metadata.name
        }}
        if (scope.metadata.dtype !== "uint8") {{
            const minV = parseFloat(document.getElementById('min-value').value)
            const maxV = parseFloat(document.getElementById('max-value').value)
            params.rescale =  `${{minV}},${{maxV}}`
        }}

        const url_params = Object.keys(params).map(i => `${{i}}=${{params[i]}}`).join('&')
        let url = `{endpoint}/tiles/tilejson.json?${{url_params}}`

        map.addSource('raster', {{ type: 'raster', url: url, tileSize: 256}})
        map.addLayer({{id: 'raster', type: 'raster', source: 'raster'}})
    }}

    const switchViz = () => {{
        if (map.getLayer('raster')) map.removeLayer('raster')
        if (map.getSource('raster')) map.removeSource('raster')

        if (map.getLayer('mvt')) map.removeLayer('mvt')
        if (map.getSource('mvt')) {{ map.removeSource('mvt') }}

        const rasterType = document.getElementById('toolbar').querySelector(".active").id
        switch (rasterType) {{
            case '1b':
                set1bViz()
                break
            case '3b':
                set3bViz()
                break
            default:
                throw new Error(`Invalid ${{rasterType}}`)
        }}
    }}

    const baseName = (str) => {{
    var base = new String(str).substring(str.lastIndexOf('/') + 1);
    return base;
    }}

    const addLayer = (layerType) => {{
        if (map.getLayer('raster')) map.removeLayer('raster')
        if (map.getLayer('mvt')) map.removeLayer('mvt')

        const active_layer = document.getElementById('layer-selector')[document.getElementById('layer-selector').selectedIndex]
        const propName = active_layer.value
        const exag = parseFloat(document.getElementById('ex-value').value)

        const minV = parseFloat(document.getElementById('min-value').value)
        const maxV = parseFloat(document.getElementById('max-value').value)

        switch (layerType) {{
            case 'raster':
                map.addLayer({{id: 'raster', type: 'raster', source: 'raster'}})
                break

            case 'point':
                map.addLayer({{
                    id: 'mvt',
                    source: 'mvt',
                    'source-layer': baseName(scope.metadata.name),
                    type: 'circle',
                    paint: {{
                        'circle-color': [
                            'interpolate',
                            ['linear'],
                            ['to-number', ['get', propName]],
                            minV, '#3700f0',
                            maxV, '#ed0707'
                        ],
                        'circle-radius': {{
                            'base': 1,
                            'stops': [
                                [0, 10],
                                [9, 5]
                            ]
                        }}
                    }}
                }})
                break

            case 'polygon':
                map.addLayer({{
                    id: 'mvt',
                    source: 'mvt',
                    'source-layer': baseName(scope.metadata.name),
                    type: 'fill-extrusion',
                    paint: {{
                        'fill-extrusion-opacity': 1,
                        'fill-extrusion-height': [
                            'interpolate',
                            ['linear'],
                            ['to-number', ['get', propName]],
                            minV, 0,
                            maxV, maxV * exag
                        ],
                        'fill-extrusion-color': [
                            'interpolate',
                            ['linear'],
                            ['to-number', ['get', propName]],
                            minV, '#3700f0',
                            maxV, '#ed0707'
                        ]
                    }}
                }})
                break

            default:
                throw new Error(`Invalid ${{layerType}}`)
        }}
    }}

    document.getElementById('btn-hide').addEventListener('click', () => {{
        document.getElementById('hide-arrow').classList.toggle('off')
        document.getElementById('menu').classList.toggle('off')
    }})

    document.getElementById('viz-selector').addEventListener('change', (e) => {{
        switch (e.target.value) {{
        case 'raster':
            document.getElementById('colormap-section').classList.remove('none')
            document.getElementById('extrusion-section').classList.add('none')
            document.getElementById('vt-size-section').classList.add('none')
            break

        case 'point':
            document.getElementById('colormap-section').classList.add('none')
            document.getElementById('extrusion-section').classList.add('none')
            document.getElementById('vt-size-section').classList.remove('none')
            break

        case 'polygon':
            document.getElementById('colormap-section').classList.add('none')
            document.getElementById('extrusion-section').classList.remove('none')
            document.getElementById('vt-size-section').classList.remove('none')
            break

        default:
        }}
        switchViz()
    }})

    document.getElementById('vt-size-selector').addEventListener('change', (e) => {{
        switchViz()
    }})

    // MVT have already all the layers while for raster we need to fetch new tiles
    const updateViz = () => {{
        const newViz = document.getElementById('viz-selector').querySelector("input[name='toggle-viz']:checked").value
        if (newViz === "raster") {{
            switchViz()
        }} else {{
            addLayer(newViz)
        }}
    }}

    document.getElementById('layer-selector').addEventListener('change', () => {{
        const active_layer = document.getElementById('layer-selector')[document.getElementById('layer-selector').selectedIndex]
        updateViz()
    }})

    document.getElementById('r-selector').addEventListener('change', () => {{switchViz()}})
    document.getElementById('g-selector').addEventListener('change', () => {{switchViz()}})
    document.getElementById('b-selector').addEventListener('change', () => {{switchViz()}})

    document.getElementById('updateExag').addEventListener('click', () => {{
        updateViz()
    }})

    document.getElementById('colormap-selector').addEventListener('change', () => {{
        updateViz()
    }})

    document.getElementById('updateRescale').addEventListener('click', () => {{{{
        updateViz()
    }}}})

    const switchPane = (event) => {{
        const cur = document.getElementById('toolbar').querySelector(".active")
        const activeViz = cur.id
        const nextViz = event.id
        cur.classList.toggle('active')
        event.classList.toggle('active')

        const curSection = document.getElementById(`${{activeViz}}-section`)
        curSection.classList.toggle('active')
        const nextSection = document.getElementById(`${{nextViz}}-section`)
        nextSection.classList.toggle('active')
        switchViz()
    }}

    const addAOI = (bounds) => {{
        const geojson = {{
            "type": "FeatureCollection",
            "features": [turf.bboxPolygon(bounds)]
        }}

        map.addSource('aoi', {{ 'type': 'geojson', 'data': geojson }})

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
                'line-width': 1
            }}
        }})
        return
    }}

    const addMosaic = (mosaic) => {{
        return fetch(`{endpoint}/mosaic/info?url=${{mosaic}}`)
            .then(res => {{
                if (res.ok) return res.json()
                throw new Error('Network response was not ok.')
            }})
            .then(data => {{
                scope.metadata = data
                console.log(data)

                const nbands = scope.metadata.layers.length

                //1 band
                const layerList = document.getElementById('layer-selector')
                for (var i = 0; i < nbands; i++) {{
                    let l = document.createElement('option')
                    l.value = scope.metadata.layers[i]
                    l.setAttribute('data-indexes', `${{i + 1}}`)
                    l.text = scope.metadata.layers[i]
                    layerList.appendChild(l)
                }}

                //RGB
                const rList = document.getElementById('r-selector')
                for (var i = 0; i < nbands; i++) {{
                    let l = document.createElement('option')
                    l.value = scope.metadata.layers[i]
                    l.setAttribute('data-indexes', `${{i + 1}}`)
                    l.text = scope.metadata.layers[i]
                    layerList.appendChild(l)
                    if (i === 0) l.selected="selected"
                    rList.appendChild(l)
                }}

                const gList = document.getElementById('g-selector')
                for (var i = 0; i < nbands; i++) {{
                    let l = document.createElement('option')
                    l.value = scope.metadata.layers[i]
                    l.setAttribute('data-indexes', `${{i + 1}}`)
                    l.text = scope.metadata.layers[i]
                    layerList.appendChild(l)
                    if (i === 1) l.selected="selected"
                    gList.appendChild(l)
                }}

                const bList = document.getElementById('b-selector')
                for (var i = 0; i < nbands; i++) {{
                    let l = document.createElement('option')
                    l.value = scope.metadata.layers[i]
                    l.setAttribute('data-indexes', `${{i + 1}}`)
                    l.text = scope.metadata.layers[i]
                    layerList.appendChild(l)
                    if (nbands > 2 && i === 2) {{
                        l.selected="selected"
                    }} else {{
                        l.selected="selected"
                    }}
                    bList.appendChild(l)
                }}

                document.getElementById('minzoom').textContent = scope.metadata.minzoom.toString()
                document.getElementById('maxzoom').textContent = scope.metadata.maxzoom.toString()
                document.getElementById('dtype').textContent = scope.metadata.dtype

                // remove loader
                document.getElementById('loader').classList.toggle('off')
                document.getElementById('hide-arrow').classList.toggle('off')
                document.getElementById('menu').classList.toggle('off')

                const bounds = scope.metadata.bounds
                map.fitBounds([[bounds[0], bounds[1]], [bounds[2], bounds[3]]])
                addAOI(bounds)

                if (nbands === 1) {{
                    document.getElementById('3b').classList.add('disabled')
                    document.getElementById('3b').classList.remove('active')
                    document.getElementById('3b-section').classList.toggle('active')
                    document.getElementById('1b').classList.add('active')
                    document.getElementById('1b-section').classList.toggle('active')
                }}

                if (scope.metadata.dtype !== "uint8") {{
                    document.getElementById('rescale-section').classList.toggle('none')
                }}

                switchViz()
                return true
            }})
    }}

    document.getElementById('launch').addEventListener('click', () => {{
        addMosaic(document.getElementById('mosaic').value)
            .then(() => {{
                document.getElementById('selector').classList.toggle('none')
            }})
            .catch(err => {{
                console.warn(err)
            }})
    }})

    map.on('load', () => {{
        map.on('mousemove', (e) => {{
            if (!map.getLayer('mvt')) return
            const mouseRadius = 1
            const feature = map.queryRenderedFeatures([
                [e.point.x - mouseRadius, e.point.y - mouseRadius],
                [e.point.x + mouseRadius, e.point.y + mouseRadius]
            ], {{ layers: ['mvt'] }})[0]
            if (feature) {{
                map.getCanvas().style.cursor = 'pointer'
            }} else {{
                map.getCanvas().style.cursor = 'inherit'
            }}
        }})

        map.on('click', 'mvt', (e) => {{
            let html = '<table><tr><th class="align-l">property</th><th class="px3 align-r">value</th></tr>'
            Object.entries(e.features[0].properties).forEach(entry => {{
                let key = entry[0]
                let value = entry[1]
                if (key !== 'id') html += `<tr><td>${{key}}</td><td class="px3 align-r">${{value}}</td></tr>`
            }})
            html += `<tr><td class="align-l">lon</td><td class="px3 align-r">${{e.lngLat.lng.toString().slice(0, 7)}}</td></tr>`
            html += `<tr><td class="align-l">lat</td><td class="px3 align-r">${{e.lngLat.lat.toString().slice(0, 7)}}</td></tr>`
            html += '</table>'
            new mapboxgl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(html)
                .addTo(map)
        }})

        // we cannot click on raster layer
        map.on('click', (e) => {{
            const bounds = scope.metadata.bounds
            if (
                (e.lngLat.lng >= bounds[0] && e.lngLat.lng <= bounds[2]) &&
                (e.lngLat.lat >= bounds[1] && e.lngLat.lat <= bounds[3])
            ) {{
                fetch(`{endpoint}/tiles/point?lng=${{e.lngLat.lng}}&lat=${{e.lngLat.lat}}&url=${{scope.metadata.name}}`)
                .then(res => {{
                    if (res.ok) return res.json()
                    throw new Error('Network response was not ok.');
                }})
                .then(data => {{
                    console.log(data)
                    let html = '<table><tr><th class="align-l">property</th><th class="px3 align-r">value</th></tr>'
                    for (var ii = 0; ii < scope.metadata.layers.length; ii++) {{
                    html += `<tr><td class="align-l">${{scope.metadata.layers[ii]}}</td><td class="px3 align-r">${{data.values[0].values[ii]}}</td></tr>`
                    }}
                    html += `<tr><td class="align-l">lon</td><td class="px3 align-r">${{e.lngLat.lng.toString().slice(0, 7)}}</td></tr>`
                    html += `<tr><td class="align-l">lat</td><td class="px3 align-r">${{e.lngLat.lat.toString().slice(0, 7)}}</td></tr>`
                    html += '</table>'
                    new mapboxgl.Popup()
                    .setLngLat(e.lngLat)
                    .setHTML(html)
                    .addTo(map)
                }})
                .catch(err => {{
                    console.warn(err)
                }})
            }}
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
