#!/bin/bash
echo "-----------------------"
echo "Creating lambda package"
echo "-----------------------"
echo "Remove uncompiled python scripts"
# Leave module precompiles for faster Lambda startup
cd ${PYTHONUSERBASE}/lib/python3.7/site-packages/
find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[2-3][0-9]//'); cp $f $n; done;
find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
find . -type f -a -name '*.py' -print0 | xargs -0 rm -f

echo "Create archive"
zip -r9q /tmp/package.zip *

cp /tmp/package.zip /local/package.zip