"""cogeo-mosaic cache configuration"""

import pydantic


class CacheSettings(pydantic.BaseSettings):
    """Application settings"""

    # TTL of the cache in seconds
    ttl: int = 300

    # Maximum size of the LRU cache in MB
    maxsize: int = 512

    # Whether or not caching is enabled
    disable: bool = False

    class Config:
        """model config"""

        env_prefix = "COGEO_MOSAIC_CACHE_"

    @pydantic.root_validator
    def check_enable(cls, values):
        """Check if cache is desabled."""
        if values.get("disable"):
            values["ttl"] = 0
            values["maxsize"] = 0
        return values


cache_config = CacheSettings()
