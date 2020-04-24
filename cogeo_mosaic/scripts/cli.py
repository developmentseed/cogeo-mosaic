"""Cogeo-mosaic: cli."""

import os
import json
import multiprocessing
from pkg_resources import iter_entry_points

from click_plugins import with_plugins
import click
import cligj

from cogeo_mosaic import version as cogeo_mosaic_version
from cogeo_mosaic.utils import get_footprints, update_mosaic
from cogeo_mosaic.mosaic import MosaicJSON
from cogeo_mosaic.backends import MosaicBackend
from cogeo_mosaic.overviews import create_low_level_cogs

from rasterio.rio import options
from rio_cogeo.profiles import cog_profiles


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
    quiet,
):
    """Create mosaic definition file."""
    input_files = input_files.read().splitlines()
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

    if output:
        with MosaicBackend(output, mosaic_def=mosaicjson) as mosaic:
            mosaic.write()
    else:
        click.echo(json.dumps(mosaicjson.dict(exclude_none=True)))


@cogeo_cli.command(short_help="Create mosaic definition from GeoJSON collection")
@cligj.features_in_arg
@click.option("--output", "-o", type=click.Path(exists=False), help="Output file name")
@click.option(
    "--minzoom",
    type=int,
    help="An integer to overwrite the minimum zoom level derived from the COGs.",
    required=True,
)
@click.option(
    "--maxzoom",
    type=int,
    help="An integer to overwrite the maximum zoom level derived from the COGs.",
    required=True,
)
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

    if output:
        with MosaicBackend(output, mosaic_def=mosaicjson) as mosaic:
            mosaic.write()
    else:
        click.echo(json.dumps(mosaicjson.dict(exclude_none=True)))


@cogeo_cli.command(short_help="Create mosaic definition from list of files")
@click.argument("input_files", type=click.File(mode="r"), default="-")
@click.argument("input_mosaic", type=click.Path())
@click.option("--output", "-o", type=click.Path(exists=False), help="Output file name")
@click.option("--min-tile-cover", type=float, help="Minimum % overlap")
@click.option(
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
def update(input_files, input_mosaic, output, min_tile_cover, threads):
    """Update mosaic definition file."""
    input_files = input_files.read().splitlines()

    # TODO: Won't work for DynamoDB
    with MosaicBackend(input_mosaic) as mosaic:
        mosaic_def = mosaic.mosaic_def.dict()

    mosaicjson = update_mosaic(
        input_files, mosaic_def, minimum_tile_cover=min_tile_cover, max_threads=threads
    )

    if output:
        with MosaicBackend(output, mosaic_def=mosaicjson) as mosaic:
            mosaic.write()
    else:
        click.echo(json.dumps(mosaicjson))


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


@cogeo_cli.command(short_help="[EXPERIMENT] Create COG overviews for a mosaic")
@click.argument("input_mosaic", type=click.Path())
@click.option(
    "--cog-profile",
    "-p",
    "cogeo_profile",
    type=click.Choice(cog_profiles.keys()),
    default="deflate",
    help="CloudOptimized GeoTIFF profile (default: deflate).",
)
@click.option("--prefix", type=str, help="Output files prefix")
@click.option(
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
@click.option(
    "--overview-level",
    type=int,
    default=6,
    help="Max internal overivew level for the COG. "
    f"Will be used to get the size of each COG. Default is {256 * 2 **6}",
)
@options.creation_options
def overview(
    input_mosaic, cogeo_profile, prefix, threads, overview_level, creation_options
):
    """Create COG overviews for a mosaic."""
    output_profile = cog_profiles.get(cogeo_profile)
    output_profile.update(dict(BIGTIFF=os.environ.get("BIGTIFF", "IF_SAFER")))
    if creation_options:
        output_profile.update(creation_options)

    config = dict(
        GDAL_NUM_THREADS="ALL_CPU",
        GDAL_TIFF_INTERNAL_MASK=os.environ.get("GDAL_TIFF_INTERNAL_MASK", True),
        GDAL_TIFF_OVR_BLOCKSIZE="128",
    )
    if not prefix:
        prefix = os.path.basename(input_mosaic).split(".")[0]

    create_low_level_cogs(
        input_mosaic,
        output_profile,
        prefix,
        max_overview_level=overview_level,
        config=config,
        threads=threads,
    )
