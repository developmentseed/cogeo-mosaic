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
from cogeo_mosaic.utils import create_mosaic, get_footprints
from cogeo_mosaic.handlers.api import APP


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
    "--threads",
    type=int,
    default=lambda: os.environ.get("MAX_THREADS", multiprocessing.cpu_count() * 5),
    help="threads",
)
def create(input_files, output, threads):
    """Create mosaic definition file."""
    input_files = input_files.read().splitlines()
    mosaic_spec = create_mosaic(input_files, max_threads=threads)

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
def footprint(input_files, output, threads):
    """Create mosaic definition file."""
    input_files = input_files.read().splitlines()
    foot = {
        "features": get_footprints(input_files, max_threads=threads),
        "type": "FeatureCollection",
    }

    if output:
        with open(output, mode="w") as f:
            f.write(json.dumps(foot))
    else:
        click.echo(json.dumps(foot))


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
            request = {
                "headers": dict(self.headers),
                "path": q.path,
                "queryStringParameters": dict(parse_qsl(q.query)),
                "httpMethod": self.command,
            }
            response = APP(request, None)

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
            body = self.rfile.read(int(dict(self.headers).get("Content-Length")))

            request = {
                "headers": dict(self.headers),
                "path": q.path,
                "queryStringParameters": dict(parse_qsl(q.query)),
                "body": body,
                "httpMethod": self.command,
            }

            response = APP(request, None)

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
