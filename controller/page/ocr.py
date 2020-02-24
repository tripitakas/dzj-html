#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: OCR相关api，供小欧调用
@time: 2019/5/13
"""
import logging
from bson.objectid import ObjectId
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.page.tool import PageTool
from controller.task.base import TaskHandler


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
                    'locked_by': self.username,
                    'locked_user_id': self.user_id,
                    'locked_time': self.now()
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
            size = int(self.data.get('size') or 1)
            condition = {'task_type': data_task, 'status': self.STATUS_PUBLISHED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_data_response(dict(tasks=None))

            # 批量获取任务
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': dict(
                status=self.STATUS_FETCHED, picked_time=self.now(), updated_time=self.now(),
                picked_user_id=self.user_id, picked_by=self.username
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
            rules = [(v.not_empty, 'tasks')]
            self.validate(self.data, rules)

            task_ids = [ObjectId(t['task_id']) for t in self.data['tasks']]
            if task_ids:
                self.db.task.update_many({'_id': {'$in': task_ids}}, {'$set': {'status': self.STATUS_PICKED}})
                self.send_data_response()
            else:
                self.send_error_response(e.no_object)

        except DbError as error:
            return self.send_db_error(error)


class SubmitOcrTasksApi(TaskHandler):
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
            rules = [(v.not_empty, 'tasks')]
            self.validate(self.data, rules)

            tasks = []
            for task in self.data['tasks']:
                r = self.submit_one(task)
                message = '' if r is True else r
                status = 'success' if r is True else 'failed'
                tasks.append(dict(ocr_task_id=task['ocr_task_id'], task_id=task['task_id'], status=status,
                                  page_name=task.get('page_name'), message=message))
            self.send_data_response(dict(tasks=tasks))

        except DbError as error:
            return self.send_db_error(error)

    def submit_one(self, task):
        _task = self.db.task.find_one({'_id': ObjectId(task['task_id']), 'task_type': task['task_type']})
        if not _task:
            return e.task_not_existed
        elif _task['picked_user_id'] != self.user_id:
            return e.task_unauthorized_locked
        page_name = self.prop(task, 'page_name')
        if page_name and page_name != _task.get('doc_id'):
            return e.doc_id_not_equal

        try:
            if task['task_type'] in ['ocr_box', 'ocr_text']:
                return self.submit_ocr(task)
            elif task['task_type'] == 'upload_cloud':
                return self.submit_upload_cloud(task)
            elif task['task_type'] == 'import_image':
                return self.submit_import_image(task)
        except DbError as error:
            return error

    def submit_ocr(self, task):
        """ 提交OCR任务 """
        now = self.now()
        page_name, result, message = task.get('page_name'), task['result'], task.get('message')
        if task['status'] == 'failed' or result.get('status') == 'failed':
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
                'status': self.STATUS_FAILED, 'updated_time': now, 'result': result, 'message': message
            }})
        else:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return e.no_object
            # ocr_text任务不允许修改切分信息
            box_changed = task['task_type'] == 'ocr_text' and PageTool.is_box_changed(result, page)
            if box_changed:
                return e.box_not_identical[0], '(%s)切分信息不一致' % box_changed
            # 更新task
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': {
                'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            })
            # 更新page，释放数据锁，更新任务状态
            ocr, ocr_col = result.get('ocr', ''), result.get('ocr_col', '')
            ocr = '|'.join(ocr) if isinstance(ocr, list) else ocr
            ocr_col = '|'.join(ocr_col) if isinstance(ocr_col, list) else ocr_col
            width = result.get('width') or page.get('width')
            height = result.get('height') or page.get('height')
            chars = result.get('chars') or page.get('chars')
            blocks = result.get('blocks') or page.get('blocks')
            columns = result.get('columns') or page.get('columns')
            self.db.page.update_one({'name': page_name}, {'$set': {
                'width': width, 'height': height, 'chars': chars, 'blocks': blocks, 'columns': columns,
                'ocr': ocr, 'ocr_col': ocr_col, 'tasks.%s' % task['task_type']: self.STATUS_FINISHED,
                'lock.box': {},
            }})
        return True

    def submit_upload_cloud(self, task):
        """ 提交upload_cloud任务。page中包含有云端路径img_cloud_path """
        now = self.now()
        page_name, result, message = task.get('page_name'), task['result'], task.get('message')
        task_update = {'updated_time': now, 'result': result, 'message': message}
        if task['status'] == 'failed' or result.get('status') == 'failed':
            task_update.update({'status': self.STATUS_FAILED, 'finished_time': now})
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        else:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return e.no_object
            task_update.update({'status': self.STATUS_FINISHED, 'finished_time': now})
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
            page_update = dict(img_cloud_path=self.prop(task, 'result.img_cloud_path'))
            self.db.page.update_one({'name': page_name}, {'$set': page_update})
        return True

    def submit_import_image(self, task):
        """ 提交import_image任务 """
        now = self.now()
        result, message = task.get('result') or {}, task.get('message')
        if task['status'] == 'failed' or result.get('status') == 'failed':
            task_update = {'status': self.STATUS_FAILED, 'updated_time': now, 'result': result, 'message': message}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        else:
            task_update = {'status': self.STATUS_FINISHED, 'finished_time': now, 'updated_time': now}
            self.db.task.update_one({'_id': ObjectId(task['task_id'])}, {'$set': task_update})
        return True
