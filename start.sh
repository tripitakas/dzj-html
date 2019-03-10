#!/bin/sh
kill -9 `ps -ef | grep 8000 | grep main.py | awk -F" " {'print $2'}` 2>/dev/null
cd `dirname $0`
test -d log || mkdir log
find `dirname $0` -name "*.pyc" | xargs rm -rf
nohup python3 main.py --port=8000 --debug=true >> log/app.log 2>&1 &
