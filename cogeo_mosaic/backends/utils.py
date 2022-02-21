"""cogeo-mosaic.backends utility functions."""

import hashlib
import json
import zlib
from typing import Any, Dict


def _compress_gz_json(data: Dict) -> bytes:
    gzip_compress = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS | 16)

    return (
        gzip_compress.compress(json.dumps(data).encode("utf-8")) + gzip_compress.flush()
    )


def _decompress_gz(gzip_buffer: bytes):
    return zlib.decompress(gzip_buffer, zlib.MAX_WBITS | 16).decode()


def get_hash(**kwargs: Any) -> str:
    """Create hash from a dict."""
    return hashlib.sha224(
        json.dumps(kwargs, sort_keys=True, default=str).encode()
    ).hexdigest()
