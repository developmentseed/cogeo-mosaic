"""cogeo-mosaic cache configuration"""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    """Application settings"""

    # TTL of the cache in seconds
    ttl: int = 300

    # Maximum size of the LRU cache in MB
    maxsize: int = 512

    # Whether or not caching is enabled
    disable: bool = False

    model_config = SettingsConfigDict(env_prefix="COGEO_MOSAIC_CACHE_")

    @model_validator(mode="before")
    def check_enable(cls, values):
        """Check if cache is disabled."""
        if values.get("disable"):
            values["ttl"] = 0
            values["maxsize"] = 0

        return values


cache_config = CacheSettings()
