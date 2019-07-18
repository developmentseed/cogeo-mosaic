#!/bin/bash
python3 -c 'from cogeo_mosaic import version as mos_version; print(mos_version)'

echo "/tilejson.json " && python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/tilejson.json", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo
echo "/info " && python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/info", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo
echo "MVT"
python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/8/134/101.pbf", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/8/134/101.pbf", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz", "feature_type": "polygon"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo
echo "RASTER"
python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/9/269/201.png", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz", "indexes": "1", "rescale": "0,255"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None); print("OK") if resp["statusCode"] == 200 else print("NOK")'
python3 -c 'from cogeo_mosaic.handlers.api import APP; resp = APP({"path": "/9/269/201.jpg", "queryStringParameters": {"url": "https://s3.amazonaws.com/opendata.remotepixel.ca/facebook/mosaic.json.gz", "indexes": "1", "rescale": "0,15", "color_map": "cfastie"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET", "headers": {}}, None);  print("OK") if resp["statusCode"] == 200 else print("NOK")'
echo
echo "Done"