# Demo

Create a Cloud Optimized GeoTIFF mosaic from Digitalglobe Opendata disaster dataset for the 2019/2020 Australian fire.

![](https://user-images.githubusercontent.com/10407788/73187922-22e54180-40f0-11ea-94c2-88bf54667513.png)

# Get data

#### Get list of files

##### Requirements
```bash
$ pip install bs4 requests rasterio
```

```python

import os
import json
import rasterio
import requests
import bs4 as BeautifulSoup

from concurrent import futures
from rasterio.warp import transform_bounds

import bs4 as BeautifulSoup

url = "https://www.digitalglobe.com/ecosystem/open-data/australia-wildfires"

# Read Page
r = requests.get(url)
soup = BeautifulSoup.BeautifulSoup(r.text)
s = soup.findAll('a')


list_file = list(set([l.get('href') for l in s if  l.get('href').endswith(".tif")]))

files = [
    dict(
        date=l.split("/")[6],
        tags=[l.split("/")[5]],
        path=l,
        sceneid=l.split("/")[7],
        preview=f"https://api.discover.digitalglobe.com/show?id={l.split('/')[7]}&f=jpeg",
        event=l.split("/")[4],
    )
    for l in list_file
]

files = sorted(files, key=lambda x:x["date"])

print(f"Number of GeoTIFF: {len(list_file)}")
with open("list_files.txt", "w") as f:
    f.write("\n".join(files))
```

# Create Mosaic Definition

Spec: https://github.com/developmentseed/mosaicjson-spec


```bash 
$ pip install https://github.com/developmentseed/cogeo-mosaic

# Use `cog-mosaic` CLI
$ cat list_files.txt | cogeo-mosaic create | gzip > mosaic.json.gz

# Upload mosaic definition
$ aws s3 cp mosaic.json.gz s3://{my-bucket}/digitalglobe/post_idai/20190320/mosaic.json.gz
```

# Mosaic Tiler

### Deploy
```bash
$ git clone https://github.com/developmentseed/cogeo-mosaic-tiler.git

# Create lambda package
$ docker-compose build --no-cache
$ docker-compose run --rm package

# Deploy
$ npm install serverless -g 
$ sls deploy
```

### Edit [/index.html](index.html)

### Open [/index.html](index.html)
