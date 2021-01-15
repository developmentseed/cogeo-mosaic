"""cogeo_mosaic.backends."""

from typing import Any, Callable, Dict, Sequence, Type, Union
from urllib.parse import urlparse

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.dynamodb import DynamoDBBackend
from cogeo_mosaic.backends.file import FileBackend
from cogeo_mosaic.backends.s3 import S3Backend
from cogeo_mosaic.backends.sqlite import SQLiteBackend
from cogeo_mosaic.backends.stac import STACBackend
from cogeo_mosaic.backends.web import HttpBackend


class Backends:
    """Backend."""

    backends: Dict = {}

    @classmethod
    def register(
        cls,
        scheme: Union[str, Sequence[str]],
        backend: Type[BaseBackend],
        uri_converter: Callable = lambda x: x,
    ):
        """Register new backend."""
        if isinstance(scheme, str):
            scheme = (scheme,)

        for sch in scheme:
            cls.backends.update({sch: (backend, uri_converter)})


Backends.register(("file", "default"), FileBackend, lambda x: urlparse(x).path)
Backends.register(("http", "https"), HttpBackend)
Backends.register("s3", S3Backend)
Backends.register("dynamodb", DynamoDBBackend)
Backends.register("sqlite", SQLiteBackend)
Backends.register(
    ("stac+http", "stac+https"), STACBackend, lambda x: x.replace("stac+", "")
)


def MosaicBackend(url: str, *args: Any, **kwargs: Any) -> BaseBackend:
    """Select mosaic backend for url."""
    parsed = urlparse(url)
    scheme = parsed.scheme or "default"

    try:
        backend_class, convertor = Backends.backends[scheme]
    except KeyError:
        raise ValueError(f"No backend registered for scheme: {scheme}")

    return backend_class(convertor(url), *args, **kwargs)
