FROM remotepixel/amazonlinux:gdal3.0-py3.7-build

WORKDIR /tmp

ENV PACKAGE_PREFIX /tmp/python

RUN pip install --upgrade pip
RUN pip install cython==0.28

COPY setup.py setup.py
COPY cogeo_mosaic/ cogeo_mosaic/

# Install dependencies
RUN pip3 install . --no-binary numpy,shapely,rasterio -t $PACKAGE_PREFIX -U
