"""cogeo_mosaic.backends."""

from typing import Any, Callable, Sequence, Type, Union
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

    backends = {
        "file": (FileBackend, lambda x: urlparse(x).path),
        "http": (HttpBackend, lambda x: x),
        "https": (HttpBackend, lambda x: x),
        "s3": (S3Backend, lambda x: x),
        "dynamodb": (DynamoDBBackend, lambda x: x),
        "sqlite": (SQLiteBackend, lambda x: x),
        "stac+http": (STACBackend, lambda x: x.replace("stac+", "")),
        "stac+https": (STACBackend, lambda x: x.replace("stac+", "")),
    }

    def get(self, url: str, *args: Any, **kwargs: Any) -> BaseBackend:
        """Get Backend."""
        parsed = urlparse(url)
        if not parsed.scheme:
            return FileBackend(parsed.path, *args, **kwargs)

        try:
            backend_class, convertor = self.backends[parsed.scheme]
        except KeyError:
            raise ValueError(f"No backend registered for scheme: {parsed.scheme}")

        return backend_class(convertor(url), *args, **kwargs)

    def register(
        self,
        scheme: Union[str, Sequence[str]],
        backend: Type[BaseBackend],
        uri_converter: Callable = lambda x: x,
    ):
        """Register new backend.

        Examples:
            >>> instance.register("local", FileBackend, lambda x: urlparse(x).path)

        """
        if isinstance(scheme, str):
            scheme = (scheme,)

        for sch in scheme:
            self.backends.update({sch: (backend, uri_converter)})


backends = Backends()


def MosaicBackend(url: str, *args: Any, **kwargs: Any) -> BaseBackend:
    """Select mosaic backend for url."""
    return backends.get(url, *args, **kwargs)
