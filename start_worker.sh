#!/bin/sh
cd `dirname $0`
test -d log || mkdir log
rm -f log/*.wk
nohup python3 periodic/release_lock.py --uri="$1" --db_name="$2"  >> log/release_lock.log 2>&1 &
nohup python3 periodic/republish_task.py --uri="$1" --db_name="$2" >> log/republish_task.log 2>&1 &
nohup python3 periodic/statistic.py --uri="$1" --db_name="$2" >> log/statistic.log 2>&1 &
