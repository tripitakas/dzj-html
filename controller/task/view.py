#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from bson import json_util
from bson.objectid import ObjectId
from controller import errors as e
from controller.task.base import TaskHandler


class TaskInfoHandler(TaskHandler):
    URL = '/task/info/@task_id'

    def get(self, task_id):
        """ 任务详情"""
        try:
            task = self.db.task.find_one({'_id': ObjectId(task_id)})
            if not task:
                self.send_error_response(e.no_object, message='没有找到该任务')
            self.render('task_info.html', task=task)

        except Exception as error:
            return self.send_db_error(error)


class TaskSampleHandler(TaskHandler):
    URL = '/task/sample/@task_type'

    def get(self, task_type):
        """ 练习任务"""
        try:
            aggregate = [{'$match': {'task_type': task_type, 'is_sample': True}}, {'$sample': {'size': 1}}]
            tasks = list(self.db.task.aggregate(aggregate))
            if tasks:
                return self.redirect('/task/%s/%s' % (task_type, tasks[0]['_id']))
            else:
                return self.send_error_response(e.no_object, message='没有找到练习任务')

        except Exception as error:
            return self.send_db_error(error)
