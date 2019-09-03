"""cogeo-mosaic.handlers.api_web: handle request for cogeo-mosaic endpoints."""

from typing import Tuple
from cogeo_mosaic import templates
from lambda_proxy.proxy import API

app = API(name="cogeo-mosaic-web", add_docs=False, debug=True)


@app.route("/", methods=["GET"], cors=True, tag=["landing page"])
@app.route("/index.html", methods=["GET"], cors=True, tag=["landing page"])
def _index() -> Tuple[str, str, str]:
    """
    Handle / requests.

    Returns
    -------
    status : str
        Status of the response (e.g. OK, NOK).
    MIME type : str
        response body MIME type (e.g. text/html).
    body : str
        String encoded html

    """
    return ("OK", "text/html", templates.index(app.host))


@app.route("/favicon.ico", methods=["GET"], cors=True, tag=["other"])
def favicon() -> Tuple[str, str, str]:
    """Favicon."""
    return ("EMPTY", "text/plain", "")
