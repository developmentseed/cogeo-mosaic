"""Cogeo-mosaic: cli."""

import json
import multiprocessing
import os

import click
import cligj
import morecantile
from click_plugins import with_plugins
from pkg_resources import iter_entry_points

from cogeo_mosaic import __version__ as cogeo_mosaic_version
from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.utils import get_footprints

tms = morecantile.tms.get("WebMercatorQuad")


@with_plugins(iter_entry_points("cogeo_mosaic.plugins"))
@click.group()
@click.version_option(version=cogeo_mosaic_version, message="%(version)s")
def cogeo_cli():
    """cogeo_mosaic cli."""
    pass


@cogeo_cli.command(short_help="Create mosaic definition from list of files")
@click.argument("input_files", type=click.File(mode="r"), default="-")
@click.option("--output", "-o", type=click.Path(exists=False), help="Output file name")
@click.option(
    "--minzoom",
    type=int,
    help="An integer to overwrite the minimum zoom level derived from the COGs.",
)
@click.option(
    "--maxzoom",
    type=int,
    help="An integer to overwrite the maximum zoom level derived from the COGs.",
)
@click.option(
    "--quadkey-zoom",
    type=int,
    help="An integer to overwrite the quadkey zoom level used for keys in the MosaicJSON.",
)
@click.option("--min-tile-cover", type=float, help="Minimum % overlap")
@click.option(
    "--tile-cover-sort", help="Sort files by covering %", is_flag=True, default=False
)
@click.option(
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
@click.option("--name", type=str, help="Mosaic name")
@click.option("--description", type=str, help="Mosaic description")
@click.option("--attribution", type=str, help="Image attibution")
@click.option(
    "--quiet",
    "-q",
    help="Remove progressbar and other non-error output.",
    is_flag=True,
    default=False,
)
def create(
    input_files,
    output,
    minzoom,
    maxzoom,
    quadkey_zoom,
    min_tile_cover,
    tile_cover_sort,
    threads,
    name,
    description,
    attribution,
    quiet,
):
    """Create mosaic definition file."""
    input_files = [file.strip() for file in input_files if file.strip()]
    mosaicjson = MosaicJSON.from_urls(
        input_files,
        minzoom=minzoom,
        maxzoom=maxzoom,
        quadkey_zoom=quadkey_zoom,
        minimum_tile_cover=min_tile_cover,
        tile_cover_sort=tile_cover_sort,
        max_threads=threads,
        quiet=quiet,
    )

    if name:
        mosaicjson.name = name
    if description:
        mosaicjson.description = description
    if attribution:
        mosaicjson.attribution = attribution

    if output:
        with MosaicBackend(output, mosaic_def=mosaicjson) as mosaic:
            mosaic.write(overwrite=True)
    else:
        click.echo(mosaicjson.json(exclude_none=True))


@cogeo_cli.command(short_help="Upload mosaic definition to backend")
@click.argument("file", type=click.File(mode="r"), default="-")
@click.option(
    "--url", type=str, required=True, help="URL to which the mosaic should be uploaded."
)
def upload(file, url):
    """Upload mosaic definition file."""
    mosaicjson = json.load(file)

    with MosaicBackend(url, mosaic_def=mosaicjson) as mosaic:
        mosaic.write(overwrite=True)


@cogeo_cli.command(
    short_help="Create mosaic definition from GeoJSON features or features collection"
)
@cligj.features_in_arg
@click.option("--output", "-o", type=click.Path(exists=False), help="Output file name")
@click.option("--minzoom", type=int, help="Mosaic minimum zoom level.", required=True)
@click.option("--maxzoom", type=int, help="Mosaic maximum zoom level.", required=True)
@click.option("--property", type=str, help="Define accessor property", required=True)
@click.option(
    "--quadkey-zoom",
    type=int,
    help="An integer to overwrite the quadkey zoom level used for keys in the MosaicJSON.",
)
@click.option("--min-tile-cover", type=float, help="Minimum % overlap")
@click.option(
    "--tile-cover-sort", help="Sort files by covering %", is_flag=True, default=False
)
@click.option("--name", type=str, help="Mosaic name")
@click.option("--description", type=str, help="Mosaic description")
@click.option("--attribution", type=str, help="Image attibution")
@click.option(
    "--quiet",
    "-q",
    help="Remove progressbar and other non-error output.",
    is_flag=True,
    default=False,
)
def create_from_features(
    features,
    output,
    minzoom,
    maxzoom,
    property,
    quadkey_zoom,
    min_tile_cover,
    tile_cover_sort,
    name,
    description,
    attribution,
    quiet,
):
    """Create mosaic definition file."""
    mosaicjson = MosaicJSON.from_features(
        list(features),
        minzoom,
        maxzoom,
        quadkey_zoom=quadkey_zoom,
        accessor=lambda feature: feature["properties"][property],
        minimum_tile_cover=min_tile_cover,
        tile_cover_sort=tile_cover_sort,
        quiet=quiet,
    )

    if name:
        mosaicjson.name = name
    if description:
        mosaicjson.description = description
    if attribution:
        mosaicjson.attribution = attribution

    if output:
        with MosaicBackend(output, mosaic_def=mosaicjson) as mosaic:
            mosaic.write(overwrite=True)
    else:
        click.echo(mosaicjson.json(exclude_none=True))


@cogeo_cli.command(short_help="Update a mosaic definition from list of files")
@click.argument("input_files", type=click.File(mode="r"), default="-")
@click.argument("input_mosaic", type=click.Path())
@click.option("--min-tile-cover", type=float, help="Minimum % overlap")
@click.option(
    "--add-first/--add-last",
    help="Appends dataset on top of the existing scenes.",
    is_flag=True,
    default=True,
)
@click.option(
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
@click.option(
    "--quiet",
    "-q",
    help="Remove progressbar and other non-error output.",
    is_flag=True,
    default=False,
)
def update(input_files, input_mosaic, min_tile_cover, add_first, threads, quiet):
    """Update mosaic definition file."""
    input_files = input_files.read().splitlines()
    features = get_footprints(input_files, max_threads=threads)
    with MosaicBackend(input_mosaic) as mosaic:
        mosaic.update(
            features,
            add_first=add_first,
            minimum_tile_cover=min_tile_cover,
            quiet=quiet,
        )


@cogeo_cli.command(short_help="Create geojson from list of files")
@click.argument("input_files", type=click.File(mode="r"), default="-")
@click.option("--output", "-o", type=click.Path(exists=False), help="Output file name")
@click.option(
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
@click.option(
    "--quiet",
    "-q",
    help="Remove progressbar and other non-error output.",
    is_flag=True,
    default=False,
)
def footprint(input_files, output, threads, quiet):
    """Create mosaic definition file."""
    input_files = input_files.read().splitlines()
    foot = {
        "features": get_footprints(input_files, max_threads=threads, quiet=quiet),
        "type": "FeatureCollection",
    }

    if output:
        with open(output, mode="w") as f:
            f.write(json.dumps(foot))
    else:
        click.echo(json.dumps(foot))


@cogeo_cli.command(short_help="Return info about the mosaic")
@click.argument("input", type=click.Path())
@click.option(
    "--json",
    "to_json",
    default=False,
    is_flag=True,
    help="Print as JSON.",
)
def info(input, to_json):
    """Return info about the mosaic."""
    with MosaicBackend(input) as mosaic:
        _info = {
            "Path": input,
            "Backend": mosaic._backend_name,
            "File Size": mosaic._file_byte_size,
            "Compressed": True if input.endswith(".gz") else False,
        }

        profile = {
            "MosaicJSON": mosaic.mosaic_def.mosaicjson,
            "Version": mosaic.mosaic_def.version,
            "Name": mosaic.mosaic_def.name,
            "Description": mosaic.mosaic_def.description,
            "Attribution": mosaic.mosaic_def.attribution,
        }

        geo = {
            "TileMatrixSet": "WebMercatorQuad",
            "BoundingBox": mosaic.mosaic_def.bounds,
            "Center": mosaic.mosaic_def.center,
            "Min Zoom": mosaic.mosaic_def.minzoom,
            "Max Zoom": mosaic.mosaic_def.maxzoom,
            "QuadKey Zoom": mosaic.mosaic_def.quadkey_zoom,
        }

        tiles = {}
        mosaic_tiles = mosaic.mosaic_def.tiles
        if mosaic_tiles:
            tiles["Nb Tiles"] = len(mosaic_tiles.keys())
            file_numb = [len(t) for t in mosaic_tiles.values()]
            tiles["Min Files"] = min(file_numb)
            tiles["Max Files"] = max(file_numb)
            tiles["Mean Files"] = round(sum(file_numb) / len(file_numb), 2)

    if to_json:
        output = _info.copy()
        output["Profile"] = profile
        output["GEO"] = geo
        output["TILES"] = tiles
        click.echo(json.dumps(output))
    else:
        sep = 25
        click.echo(
            f"""{click.style('File:', bold=True)} {_info['Path']}
{click.style('Backend:', bold=True)} {_info['Backend']}
{click.style('File Size:', bold=True)} {_info['File Size']}
{click.style('Compressed:', bold=True)} {_info['Compressed']}

{click.style('Profile', bold=True)}
    {click.style("MosaicJSON:", bold=True):<{sep}} {profile['MosaicJSON']}
    {click.style("Version:", bold=True):<{sep}} {profile['Version']}
    {click.style("Name:", bold=True):<{sep}} {profile['Name']}
    {click.style("Description:", bold=True):<{sep}} {profile['Description']}
    {click.style("Attribution:", bold=True):<{sep}} {profile['Attribution']}

{click.style('Geo', bold=True)}
    {click.style("TileMatrixSet:", bold=True):<{sep}} {geo['TileMatrixSet']}
    {click.style("BoundingBox:", bold=True):<{sep}} {geo['BoundingBox']}
    {click.style("Center:", bold=True):<{sep}} {geo['Center']}
    {click.style("Min Zoom:", bold=True):<{sep}} {geo['Min Zoom']}
    {click.style("Max Zoom:", bold=True):<{sep}} {geo['Max Zoom']}
    {click.style("QuadKey Zoom:", bold=True):<{sep}} {geo['QuadKey Zoom']}

{click.style('Tiles', bold=True)}
    {click.style("Nb Tiles:", bold=True):<{sep}} {tiles.get('Nb Tiles')}
    {click.style("Min Files:", bold=True):<{sep}} {tiles.get('Min Files')}
    {click.style("Max Files:", bold=True):<{sep}} {tiles.get('Max Files')}
    {click.style("Mean Files:", bold=True):<{sep}} {tiles.get('Mean Files')}"""
        )


@cogeo_cli.command(short_help="Create GeoJSON from a MosaicJSON document")
@click.argument("input", type=click.Path())
@click.option(
    "--collect/--features",
    is_flag=True,
    default=False,
    help="Output as a GeoJSON feature collections or as a newline-delimited GeoJSON features (default is newline-delimited).",
)
def to_geojson(input, collect):
    """Read MosaicJSON document and create GeoJSON features."""
    features = []
    with MosaicBackend(input) as mosaic:
        for qk, assets in mosaic.mosaic_def.tiles.items():
            tile = tms.quadkey_to_tile(qk)
            west, south, east, north = tms.bounds(tile)

            geom = {
                "type": "Polygon",
                "coordinates": [
                    [
                        [west, south],
                        [west, north],
                        [east, north],
                        [east, south],
                        [west, south],
                    ]
                ],
            }
            feature = {
                "type": "Feature",
                "id": str(tile),
                "geometry": geom,
                "properties": {"nb_assets": len(assets), "assets": assets},
            }

            if collect:
                features.append(feature)
            else:
                click.echo(json.dumps(feature))

        if collect and features:
            click.echo(
                json.dumps(
                    {"type": "FeatureCollection", "features": features},
                )
            )
