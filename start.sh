#!/bin/sh
if [ ! $1 ]; then
    set $1 8000
fi
kill -9 `ps -ef | grep $1 | grep main.py | awk -F" " {'print $2'}` 2>/dev/null
cd `dirname $0`
test -d log || mkdir log
find `dirname $0` -name "*.pyc" | xargs rm -rf
nohup python3 main.py --port=$1 --debug=false >> log/app.log 2>&1 &
