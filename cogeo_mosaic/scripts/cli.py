"""Cogeo-mosaic: cli."""

import os
import json
import base64
import multiprocessing
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qsl
from http.server import HTTPServer, BaseHTTPRequestHandler

import click

from cogeo_mosaic import version as cogeo_mosaic_version
from cogeo_mosaic.utils import (
    create_mosaic,
    get_footprints,
    fetch_mosaic_definition,
    update_mosaic,
)
from cogeo_mosaic.overviews import create_low_level_cogs

from rasterio.rio import options
from rio_cogeo.profiles import cog_profiles

from cogeo_mosaic.handlers.web import app as app_web
from cogeo_mosaic.handlers.tiles import app as app_tiles
from cogeo_mosaic.handlers.mosaic import app as app_mosaic


app_web.https = False
app_tiles.https = False
app_mosaic.https = False


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    """MultiThread."""

    pass


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
    min_tile_cover,
    tile_cover_sort,
    threads,
    quiet,
):
    """Create mosaic definition file."""
    input_files = input_files.read().splitlines()
    mosaic_spec = create_mosaic(
        input_files,
        minzoom=minzoom,
        maxzoom=maxzoom,
        minimum_tile_cover=min_tile_cover,
        tile_cover_sort=tile_cover_sort,
        max_threads=threads,
        quiet=quiet,
    )

    if output:
        with open(output, mode="w") as f:
            f.write(json.dumps(mosaic_spec))
    else:
        click.echo(json.dumps(mosaic_spec))


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
    mosaic_def = fetch_mosaic_definition(input_mosaic)

    mosaic_spec = update_mosaic(
        input_files, mosaic_def, minimum_tile_cover=min_tile_cover, max_threads=threads
    )

    if output:
        with open(output, mode="w") as f:
            f.write(json.dumps(mosaic_spec))
    else:
        click.echo(json.dumps(mosaic_spec))


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
    mosaic_def = fetch_mosaic_definition(input_mosaic)

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
        mosaic_def,
        output_profile,
        prefix,
        max_overview_level=overview_level,
        config=config,
        threads=threads,
    )


@cogeo_cli.command(short_help="Local Server")
@click.option("--port", type=int, default=8000, help="port")
def run(port):
    """Launch server."""
    server_address = ("", port)

    class Handler(BaseHTTPRequestHandler):
        """Requests handler."""

        def do_GET(self):
            """Get requests."""
            q = urlparse(self.path)
            pathParameters = {}
            if q.path.startswith("/tiles/"):
                application = app_tiles
                resource = "/tiles/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/tiles/", "")}
            elif q.path.startswith("/mosaic/"):
                application = app_mosaic
                resource = "/mosaic/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/mosaic/", "")}
            else:
                application = app_web
                resource = "/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/", "")}

            request = {
                "resource": resource,
                "pathParameters": pathParameters,
                "headers": dict(self.headers),
                "path": q.path,
                "queryStringParameters": dict(parse_qsl(q.query)),
                "httpMethod": self.command,
            }
            response = application(request, None)

            self.send_response(int(response["statusCode"]))
            for r in response["headers"]:
                self.send_header(r, response["headers"][r])
            self.end_headers()

            if response.get("isBase64Encoded"):
                response["body"] = base64.b64decode(response["body"])

            if isinstance(response["body"], str):
                self.wfile.write(bytes(response["body"], "utf-8"))
            else:
                self.wfile.write(response["body"])

        def do_POST(self):
            """POST requests."""
            q = urlparse(self.path)
            pathParameters = {}
            if q.path.startswith("/tiles/"):
                application = app_tiles
                resource = "/tiles/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/tiles/", "")}
            elif q.path.startswith("/mosaic/"):
                application = app_mosaic
                resource = "/mosaic/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/mosaic/", "")}
            else:
                application = app_web
                resource = "/{proxy+}"
                pathParameters = {"proxy": q.path.replace("/", "")}

            body = self.rfile.read(int(dict(self.headers).get("Content-Length")))
            body = base64.b64encode(body).decode()
            request = {
                "resource": resource,
                "pathParameters": pathParameters,
                "headers": dict(self.headers),
                "path": q.path,
                "queryStringParameters": dict(parse_qsl(q.query)),
                "body": body,
                "httpMethod": self.command,
                "isBase64Encoded": True,
            }
            response = application(request, None)

            self.send_response(int(response["statusCode"]))
            for r in response["headers"]:
                self.send_header(r, response["headers"][r])
            self.end_headers()
            if isinstance(response["body"], str):
                self.wfile.write(bytes(response["body"], "utf-8"))
            else:
                self.wfile.write(response["body"])

    httpd = ThreadingSimpleServer(server_address, Handler)
    click.echo(f"Starting local server at http://127.0.0.1:{port}", err=True)
    httpd.serve_forever()
