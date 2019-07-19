"""Setup cogeo-mosaic."""

from setuptools import setup, find_packages


# Runtime requirements.
inst_reqs = [
    "mercantile",
    "supermercado",
    "shapely",
    "requests",
    "rasterio[s3]",
    "rio-color",
    "rio_tiler>=1.2.9",
    "rio_tiler_mosaic>=0.0.1dev1",
    "rio_tiler_mvt",
    "lambda-proxy~=4.0",
]
extra_reqs = {
    "test": ["pytest", "pytest-cov", "mock"],
    "dev": ["pytest", "pytest-cov", "pre-commit", "mock"],
}

setup(
    name="cogeo-mosaic",
    version="0.0.1",
    description=u"Create and serve COG mosaics.",
    long_description=u"Create and serve COG mosaics.",
    python_requires=">=3",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="COG COGEO Mosaic GIS",
    author=u"Vincent Sarago",
    author_email="vincent@developmentseed.org",
    url="https://github.com/developmentseed/cogeo-mosaic",
    license="MIT",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
    entry_points={
        "console_scripts": ["cogeo-mosaic = cogeo_mosaic.scripts.cli:cogeo_cli"]
    },
)
