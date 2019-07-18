# Demo

![](https://user-images.githubusercontent.com/10407788/56006732-19dfcc80-5ca4-11e9-8150-082691a6d7d8.png)

# Get data

Download https://data.humdata.org/dataset/highresolutionpopulationdensitymaps

# Pre-Process

```bash

$ ls -1
population_AF01_2018-10-01.tif
population_AF02_2018-10-01.tif
population_AF03_2018-10-01.tif
...
...
population_AF28_2018-10-01.tif
```

## 1. remove overviews and add back more 

```bash
$ ls -1 | while read line; do gdaladdo -clean $line; gdaladdo $line; done
```


## 2. Create COGs

```bash
$ ls -1 | while read line; do n=$(echo $line | sed 's/\.tif/_cog\.tif/g'); gdal_translate $line $n -co TILED=YES -co COPY_SRC_OVERVIEWS=YES -co COMPRESS=DEFLATE -co BLOCKXSIZE=256 -co BLOCKYSIZE=256 -co ZLEVEL=6; done
```

Note: We could also use [rio-cogeo](https://github.com/cogeotiff/rio-cogeo)

## 3. Send data to AWS S3

```bash
$ aws s3 sync . s3://{my-bucket}/facebook/ --acl public-read
```

# Create Mosaic Definition

Spec: https://github.com/developmentseed/mosaicjson-spec


## 1. List files

```bash
$ aws s3 ls s3://{my-bucket}/facebook/ --recursive | awk '{print "s3://{my-bucket}/"$NF}' > list_fb.txt
```


## 2. Create Mosaic file

```bash 
$ pip install https://github.com/developmentseed/cogeo-mosaic

# Use `cog-mosaic` CLI
$ cat list_fb.txt | cogeo-mosaic create | gzip > mosaic.json.gz

# Upload mosaic definition
$ aws s3 cp mosaic.json.gz s3://{my-bucket}/facebook/mosaic.json.gz
```

# Mosaic Tiler

### Deploy
```bash
$ git clone https://github.com/developmentseed/cogeo-mosaic.git

# Create lambda package
$ docker-compose build --no-cache
$ docker-compose run --rm package

# Deploy
$ npm install serverless -g 
$ sls deploy
```

### Edit [/index.html](index.html)


### Open [/index.html](index.html)

![](https://user-images.githubusercontent.com/10407788/57730526-a811ee80-7666-11e9-8bb2-6cb304dc9780.jpg)
