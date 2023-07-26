from cogeo_mosaic.cache import CacheSettings


def test_cache_config(monkeypatch):
    monkeypatch.setenv("COGEO_MOSAIC_CACHE_TTL", "500")

    conf = CacheSettings()
    assert conf.ttl == 500
    assert conf.maxsize == 512

    conf = CacheSettings(disable=True)
    assert conf.ttl == 0
    assert conf.maxsize == 0
