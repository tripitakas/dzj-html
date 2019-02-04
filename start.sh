#!/bin/sh
/usr/bin/kill -9 `ps -ef | grep 443 | grep python3 | awk -F" " {'print $2'}`
cd `dirname $0`
test -d log || mkdir log
find `dirname $0` -name "*.pyc" | xargs rm -rf
nohup python3 main.py --port=443 --debug=0 >> log/app.log 2>&1 &