#!/bin/sh
cd `dirname $0`
test -d log || mkdir log
pkill -f 'python3 main.py'
find . -name "*.pyc" | xargs rm -rf
nohup python3 main.py --port=8000 >> log/app.log 2>&1 &
