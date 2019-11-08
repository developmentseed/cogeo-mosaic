
"""tests cogeo_mosaic.custom_cmaps."""

import pytest

from cogeo_mosaic import custom_cmaps


def test_cmap():
    """Should return custom colormap."""
    assert custom_cmaps.get_custom_cmap("custom_above")

    with pytest.raises(Exception):
        custom_cmaps.get_custom_cmap("above")

    with pytest.raises(KeyError):
        custom_cmaps.get_custom_cmap("custom_avobe")
