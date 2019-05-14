# Demo

Create a COG mosaic from Digitalglobe Opendata disaster dataset for cyclone Idai (2019)

![](https://user-images.githubusercontent.com/10407788/57623865-32cbee00-7580-11e9-9496-fa322788310a.png)

# Get data

#### Get list of files for post event 2019-03-20
```python
import requests

import bs4 as BeautifulSoup
url = "https://www.digitalglobe.com/ecosystem/open-data/cyclone_idai"

# Read Page
r = requests.get(url)
soup = BeautifulSoup.BeautifulSoup(r.text)
s = soup.findAll("a")

list_file = list(set([l.get("href") for l in s if "cyclone_idai/post-event/2019-03-20" in l.get('href')]))
list_file = [l for l in list_file if not l.endswith(".ovr")] 

with open("list_dg_post_idai.txt", "w") as f:
    f.write("\n".join(list_file))
```

# Pre-Process

## 1. Download and translate to COG
see [**vincentsarago/cog-translator**](https://github.com/vincentsarago/cog-translator)

# Create Mosaic Definition

Spec: https://github.com/developmentseed/mosaicjson-spec


## 1. List files

```bash
$ aws s3 ls s3://{my-bucket}/digitalglobe/post_idai/20190320/ --recursive | awk '{print "s3://{my-bucket}/"$NF}' > list_dg.txt
```


## 2. Create Mosaic file

```bash 
$ pip install https://github.com/developmentseed/cogeo-mosaic

# Use `cog-mosaic` CLI
$ cat list_fb.txt | cogeo-mosaic create | gzip > mosaic.json.gz

# Upload mosaic definition
$ aws s3 cp mosaic.json.gz s3://{my-bucket}/digitalglobe/post_idai/20190320/mosaic.json.gz
```

# Mosaic Tiler

### Deploy
```bash
$ git clone https://github.com/developmentseed/cogeo-mosaic.git

# edit main.tf / backend.tf files 
$ terraform init
$ terraform apply
```

### Edit [/index.html](index.html)


### Open [/index.html](index.html)

![](https://user-images.githubusercontent.com/10407788/57626070-aa038100-7584-11e9-8ed1-231874fd472a.jpg)

![](https://user-images.githubusercontent.com/10407788/57626024-935d2a00-7584-11e9-9aa9-91d65037f552.jpg)
