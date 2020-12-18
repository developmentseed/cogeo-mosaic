"""Setup cogeo-mosaic."""

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()

# Runtime requirements.
inst_reqs = [
    "attrs",
    "boto3",
    "mercantile",
    "morecantile",
    "pygeos>=0.7",
    "pydantic",
    "requests",
    "rasterio",
    "requests",
    "rio-tiler>=2.0.0rc4,<2.1",
    "cachetools",
    "supermercado",
]

extra_reqs = {
    "test": ["pytest", "pytest-cov"],
    "dev": ["pytest", "pytest-cov", "pre-commit"],
    "docs": ["mkdocs", "mkdocs-material", "pygments", "mkapi"],
}

setup(
    name="cogeo-mosaic",
    version="3.0.0b1",
    description=u"Create mosaicJSON.",
    long_description=readme,
    long_description_content_type="text/markdown",
    python_requires=">=3",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: GIS",
    ],
    keywords="COG Mosaic GIS",
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
