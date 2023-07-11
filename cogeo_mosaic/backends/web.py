"""cogeo-mosaic HTTP backend.

This file is named web.py instead of http.py because http is a Python standard
lib module
"""

import json
from typing import Dict, Sequence

import attr
import httpx
from cachetools import TTLCache, cached
from cachetools.keys import hashkey

from cogeo_mosaic.backends.base import BaseBackend
from cogeo_mosaic.backends.utils import _decompress_gz
from cogeo_mosaic.cache import cache_config
from cogeo_mosaic.errors import _HTTP_EXCEPTIONS, MosaicError
from cogeo_mosaic.mosaic import MosaicJSON


@attr.s
class HttpBackend(BaseBackend):
    """Http/Https Backend Adapter"""

    # Because the HttpBackend is a Read-Only backend, there is no need for
    # mosaic_def to be in the init method.
    mosaic_def: MosaicJSON = attr.ib(init=False, default=None)

    _backend_name = "HTTP"

    @cached(  # type: ignore
        TTLCache(maxsize=cache_config.maxsize, ttl=cache_config.ttl),
        key=lambda self: hashkey(self.input),
    )
    def _read(self) -> MosaicJSON:  # type: ignore
        """Get mosaicjson document."""
        try:
            r = httpx.get(self.input)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            # post-flight errors
            status_code = e.response.status_code
            exc = _HTTP_EXCEPTIONS.get(status_code, MosaicError)
            raise exc(e.response.content) from e
        except httpx.RequestError as e:
            # pre-flight errors
            raise MosaicError(e.args[0].reason) from e

        body = r.content

        self._file_byte_size = len(body)

        if self.input.endswith(".gz"):
            body = _decompress_gz(body)

        return MosaicJSON(**json.loads(body))

    def write(self, overwrite: bool = True):
        """Write mosaicjson document."""
        raise NotImplementedError

    def update(
        self,
        features: Sequence[Dict],
        add_first: bool = True,
        quiet: bool = False,
        **kwargs,
    ):
        """Update the mosaicjson document."""
        raise NotImplementedError
