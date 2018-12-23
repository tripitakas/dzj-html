#!/bin/sh
cd `dirname $0`
test -d log || mkdir log
sudo pkill -f 'python3 main.py'
find . -name "*.pyc" | sudo xargs rm -rf
sudo nohup python3 main.py --port=443 >> log/app.log 2>&1 &
