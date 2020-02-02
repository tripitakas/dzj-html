#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: OCR相关api，供小欧调用
@time: 2019/5/13
"""
import logging
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.task.base import TaskHandler
from controller.page.submit import SubmitOcrTaskHandler


class FetchOcrTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@ocr_task'

    def post(self, data_task):
        """ 批量领取数据任务"""

        def get_tasks():
            # ocr_box、ocr_text时，锁定box，以免修改
            condition = {'name': {'$in': [t['doc_id'] for t in tasks]}}
            if data_task in ['ocr_box', 'ocr_text']:
                self.db.page.update_many(condition, {'$set': {'lock.box': {
                    'is_temp': False,
                    'lock_type': dict(tasks=data_task),
                    'locked_by': self.current_user['name'],
                    'locked_user_id': self.current_user['_id'],
                    'locked_time': datetime.now()
                }}})
            # ocr_box、ocr_text时，把layout/blocks/columns/chars等参数传过去
            if data_task in ['ocr_box', 'ocr_text']:
                params = self.db.page.find(condition)
                fields = ['layout'] if data_task == 'ocr_box' else ['layout', 'blocks', 'columns', 'chars']
                params = {p['name']: {k: p.get(k) for k in fields} for p in params}
                for t in tasks:
                    t['input'] = params.get(t['doc_id'])
                    if not t['input']:
                        logging.warning('page %s not found' % t['doc_id'])

            return [dict(task_id=str(t['_id']), priority=t.get('priority'), page_name=t.get('doc_id'),
                         input=t.get('input')) for t in tasks]

        try:
            data = self.get_request_data()
            size = int(data.get('size') or 1)
            condition = {'task_type': data_task, 'status': self.STATUS_PUBLISHED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_data_response(dict(tasks=None))

            # 批量获取任务
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': dict(
                status=self.STATUS_FETCHED, picked_time=datetime.now(), updated_time=datetime.now(),
                picked_user_id=self.current_user['_id'], picked_by=self.current_user['name']
            )})
            if r.matched_count:
                logging.info('%d %s tasks fetched' % (r.matched_count, data_task))
                self.send_data_response(dict(tasks=get_tasks()))

        except DbError as error:
            return self.send_db_error(error)


class ConfirmFetchOcrTasksApi(TaskHandler):
    URL = '/api/task/confirm_fetch/@ocr_task'

    def post(self, data_task):
        """ 确认批量领取任务成功 """

        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            task_ids = [ObjectId(t['task_id']) for t in data['tasks']]
            if task_ids:
                self.db.task.update_many({'_id': {'$in': task_ids}}, {'$set': {'status': self.STATUS_PICKED}})
                self.send_data_response()
            else:
                self.send_error_response(e.no_object)

        except DbError as error:
            return self.send_db_error(error)


class SubmitOcrTasksApi(SubmitOcrTaskHandler):
    URL = '/api/task/submit/@ocr_task'

    def post(self, task_type):
        """ 批量提交数据任务。提交参数为tasks，格式如下：
        [{'task_type': '', 'ocr_task_id':'', 'task_id':'', 'page_name':'', 'status':'success', 'result':{}},
         {'task_type': '', 'ocr_task_id':'','task_id':'', 'page_name':'', 'status':'failed', 'message':''},
        ]
        其中，ocr_task_id是远程任务id，task_id是本地任务id，status为success/failed，
        result是成功时的数据，message为失败时的错误信息。
        """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            tasks = []
            for task in data['tasks']:
                r = self.submit_one(task)
                message = '' if r is True else r
                status = 'success' if r is True else 'failed'
                tasks.append(dict(ocr_task_id=task['ocr_task_id'], task_id=task['task_id'], status=status,
                                  page_name=task.get('page_name'), message=message))
            self.send_data_response(dict(tasks=tasks))

        except DbError as error:
            return self.send_db_error(error)
