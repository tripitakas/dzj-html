#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/6/23
"""
from datetime import datetime
from controller.base import DbError
from tornado.escape import json_decode
from controller.task.base import TaskHandler


class SaveCutApi(TaskHandler):
    """ 保存切分数据。相关的任务权限、数据权限等，在prepare中已检查，无须重复检查。
        1. 保存：更新数据和任务时间即可
        2. 提交：更新数据、任务时间、任务状态、释放数据锁，然后处理后置任务
     """

    def save(self, task_type, page_name):
        try:
            assert task_type in self.cut_task_names()

            data = self.get_request_data()
            data_type = self.get_data_type(task_type)
            boxes = json_decode(data.get('boxes', '[]'))

            if data.get('submit'):
                update = {
                    data_type: boxes,
                    'tasks.%s.status' % task_type: self.STATUS_FINISHED,
                    'tasks.%s.updated_time' % task_type: datetime.now(),
                    'tasks.%s.finished_time' % task_type: datetime.now(),
                    'lock.%s' % data_type: {},
                }
            else:
                update = {
                    data_type: boxes,
                    'tasks.%s.updated_time' % task_type: datetime.now(),
                }

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            if data.get('submit'):
                # 处理后置任务
                self.update_post_tasks(page_name, task_type)

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class SaveCutProofApi(SaveCutApi):
    URL = '/api/task/do/@box_type_cut_proof/@page_name'

    def post(self, kind, page_name):
        """ 保存或提交切分校对任务 """
        self.save(kind + '_cut_proof', page_name)


class SaveCutReviewApi(SaveCutApi):
    URL = '/api/task/do/@box_type_cut_review/@page_name'

    def post(self, kind, page_name):
        """ 保存或提交切分审定任务 """
        self.save(kind + '_cut_review', page_name)
