#!/bin/sh
cd `dirname $0`
test -d log || mkdir log
rm -f log/*.wk  # stop previous workers
nohup python3 periodic/republish_task.py --uri="$1" --db_name="$2" >> log/republish_task.log 2>&1 &
