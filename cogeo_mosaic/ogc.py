"""OCG wmts template."""

from typing import Tuple


def gdal_wms_template(
    endpoint: str,
    query_string: str = "",
    minzoom: int = 0,
    maxzoom: int = 25,
    tile_scale: int = 1,
    tile_format: str = "jpeg",
    nbands: int = 3,
    dtype: str = "Byte",
) -> str:
    """
    Create GDAL WMS XML template.

    Attributes
    ----------
    endpoint : str, required
        Mosaic tiler endpoint.
    query_string : str, optional
        Endpoint querystring.
    minzoom : int, optional (default: 0)
        Mosaic min zoom.
    maxzoom : int, optional (default: 25)
        Mosaic max zoom.
    tile_scale : int, optional (default: 1 -> 256px)
        Tile endpoint size scale.
    tile_format: str, optional (default: png)
        Tile image type.
    nbands: int, optional (default: 4)
    Returns
    -------
    xml : str
        GDAL Web Map Service XML template.

    """
    tilesize = 256 * tile_scale

    xml = f"""<GDAL_WMS>
        <Service name="TMS">
            <ServerUrl>{endpoint}/${{z}}/${{x}}/${{y}}@{tile_scale}x.{tile_format}?{query_string}</ServerUrl>
        </Service>
        <ImageFormat>image/{tile_format}</ImageFormat>
        <DataWindow>
            <UpperLeftX>-20037508.34</UpperLeftX>
            <UpperLeftY>20037508.34</UpperLeftY>
            <LowerRightX>20037508.34</LowerRightX>
            <LowerRightY>-20037508.34</LowerRightY>
            <TileLevel>{maxzoom}</TileLevel>
            <TileCountX>1</TileCountX>
            <TileCountY>1</TileCountY>
            <YOrigin>top</YOrigin>
        </DataWindow>
        <Projection>EPSG:3857</Projection>
        <BlockSizeX>{tilesize}</BlockSizeX>
        <BlockSizeY>{tilesize}</BlockSizeY>
        <BandsCount>{nbands}</BandsCount>
        <DataType>{dtype}</DataType>
        <OverviewCount>{maxzoom - minzoom}</OverviewCount>
        <MaxConnections>100</MaxConnections>
        <ZeroBlockHttpCodes>204,404</ZeroBlockHttpCodes>
        <ZeroBlockOnServerException>true</ZeroBlockOnServerException>
    </GDAL_WMS>"""

    return xml


def wmts_template(
    endpoint: str,
    layer_name: str,
    query_string: str = "",
    minzoom: int = 0,
    maxzoom: int = 25,
    bounds: Tuple = [-180, -85.051129, 85.051129, 180],
    tile_scale: int = 1,
    tile_format: str = "png",
    title: str = "Cloud Optimizied GeoTIFF Mosaic",
) -> str:
    """
    Create WMTS XML template.

    Attributes
    ----------
    endpoint : str, required
        Mosaic tiler endpoint.
    layer_name : str, required
        Layer name.
    query_string : str, optional
        Endpoint querystring.
    minzoom : int, optional (default: 0)
        Mosaic min zoom.
    maxzoom : int, optional (default: 25)
        Mosaic max zoom.
    bounds : tuple, optional (default: [-180, -85.051129, 85.051129, 180])
        WGS84 layer bounds.
    tile_scale : int, optional (default: 1 -> 256px)
        Tile endpoint size scale.
    tile_format: str, optional (default: png)
        Tile image type.
    title: str, optional (default: "Cloud Optimizied GeoTIFF Mosaic")
        Layer title.

    Returns
    -------
    xml : str
        OGC Web Map Tile Service (WMTS) XML template.

    """
    media_type = "tiff" if tile_format == "tif" else tile_format
    content_type = f"image/{media_type}"
    tilesize = 256 * tile_scale

    tileMatrix = []
    for zoom in range(minzoom, maxzoom + 1):
        tm = f"""<TileMatrix>
            <ows:Identifier>{zoom}</ows:Identifier>
            <ScaleDenominator>{559082264.02872 / 2 ** zoom / tile_scale}</ScaleDenominator>
            <TopLeftCorner>-20037508.34278925 20037508.34278925</TopLeftCorner>
            <TileWidth>{tilesize}</TileWidth>
            <TileHeight>{tilesize}</TileHeight>
            <MatrixWidth>{2 ** zoom}</MatrixWidth>
            <MatrixHeight>{2 ** zoom}</MatrixHeight>
        </TileMatrix>"""
        tileMatrix.append(tm)
    tileMatrix = "\n".join(tileMatrix)

    xml = f"""<Capabilities
        xmlns="http://www.opengis.net/wmts/1.0"
        xmlns:ows="http://www.opengis.net/ows/1.1"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:gml="http://www.opengis.net/gml"
        xsi:schemaLocation="http://www.opengis.net/wmts/1.0 http://schemas.opengis.net/wmts/1.0/wmtsGetCapabilities_response.xsd"
        version="1.0.0">
       <ows:ServiceIdentification>
            <ows:Title>{title}</ows:Title>
            <ows:ServiceType>OGC WMTS</ows:ServiceType>
            <ows:ServiceTypeVersion>1.0.0</ows:ServiceTypeVersion>
        </ows:ServiceIdentification>
        <ows:OperationsMetadata>
            <ows:Operation name="GetCapabilities">
                <ows:DCP>
                    <ows:HTTP>
                        <ows:Get xlink:href="{endpoint}/wmts?{query_string}">
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
                        <ows:Get xlink:href="{endpoint}/wmts?{query_string}">
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
                <ows:Title>{title}</ows:Title>
                <ows:Identifier>{layer_name}</ows:Identifier>
                <ows:Abstract>cogeo-mosaic</ows:Abstract>
                <ows:WGS84BoundingBox crs="urn:ogc:def:crs:OGC:2:84">
                    <ows:LowerCorner>{bounds[0]} {bounds[1]}</ows:LowerCorner>
                    <ows:UpperCorner>{bounds[2]} {bounds[3]}</ows:UpperCorner>
                </ows:WGS84BoundingBox>
                <Style isDefault="true">
                    <ows:Identifier>default</ows:Identifier>
                </Style>
                <Format>{content_type}</Format>
                <TileMatrixSetLink>
                    <TileMatrixSet>GoogleMapsCompatible</TileMatrixSet>
                </TileMatrixSetLink>
                <ResourceURL
                    format="{content_type}"
                    resourceType="tile"
                    template="{endpoint}/{{TileMatrix}}/{{TileCol}}/{{TileRow}}@{tile_scale}x.{tile_format}?{query_string}"/>
            </Layer>
            <TileMatrixSet>
                <ows:Title>GoogleMapsCompatible</ows:Title>
                <ows:Abstract>GoogleMapsCompatible EPSG:3857</ows:Abstract>
                <ows:Identifier>GoogleMapsCompatible</ows:Identifier>
                <ows:SupportedCRS>urn:ogc:def:crs:EPSG::3857</ows:SupportedCRS>
                {tileMatrix}
            </TileMatrixSet>
        </Contents>
        <ServiceMetadataURL xlink:href='{endpoint}/wmts?{query_string}'/>
    </Capabilities>"""

    return xml
