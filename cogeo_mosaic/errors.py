"""Custom exceptions"""


class MosaicError(Exception):
    """Base exception"""


class MosaicAuthError(MosaicError):
    """Authentication error"""


class MosaicNotFoundError(MosaicError):
    """Mosaic not found error"""


class NoAssetFoundError(MosaicError):
    """No Asset found"""


_HTTP_EXCEPTIONS = {
    401: MosaicAuthError,
    403: MosaicAuthError,
    404: MosaicNotFoundError,
}

_FILE_EXCEPTIONS = {FileNotFoundError: MosaicNotFoundError}
