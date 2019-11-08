"""custom colormaps."""

import re

# colors from https://daac.ornl.gov/ABOVE/guides/Annual_Landcover_ABoVE.html
above_cmap = {
    1: [58, 102, 24],  # Evergreen Forest
    2: [100, 177, 41],  # Deciduous Forest
    3: [177, 177, 41],  # Shrubland
    4: [221, 203, 154],  # Herbaceous
    5: [218, 203, 47],  # Sparely Vegetated
    6: [177, 177, 177],  # Barren
    7: [175, 255, 205],  # Fen
    8: [239, 255, 192],  # Bog
    9: [144, 255, 255],  # Shallows/Littoral
    10: [29, 0, 250],  # Water
}

COLOR_MAPS = {"above": above_cmap.copy()}


def get_custom_cmap(cname):
    """Return custom colormap."""
    if not re.match(r"^custom_", cname):
        raise Exception("Invalid colormap name")
    _, name = cname.split("_")
    return COLOR_MAPS[name]
