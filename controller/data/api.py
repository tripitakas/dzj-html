#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
import logging
from bson.objectid import ObjectId
from tornado.escape import to_basestring
import controller.validate as v
from controller import errors
from controller.base import BaseHandler, DbError
from .data import Tripitaka, Volume, Reel, Sutra, Page
from controller.task.base import TaskHandler
from .submit import SubmitDataTaskApi

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class DataUploadApi(BaseHandler):
    URL = '/api/data/@collection/upload'

    def post(self, collection):
        """ 批量上传 """
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel', 'page']
        collection_class = eval(collection.capitalize())
        upload_file = self.request.files.get('csv') or self.request.files.get('json')
        content = to_basestring(upload_file[0]['body'])
        with StringIO(content) as fn:
            if collection == 'page':
                r = Page.insert_new(self.db, file_stream=fn)
            else:
                update = False if collection == 'tripitaka' else True
                r = collection_class.save_many(self.db, collection, file_stream=fn, update=update)

            if r.get('status') == 'success':
                self.add_op_log('upload_%s' % collection, context=r.get('message'))
                self.send_data_response({'message': r.get('message'), 'errors': r.get('errors')})
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class DataAddOrUpdateApi(BaseHandler):
    URL = '/api/data/@collection'

    def post(self, collection):
        """ 新增或修改 """
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel']
        collection_class = eval(collection.capitalize())
        try:
            data = self.get_request_data()
            r = collection_class.save_one(self.db, collection, data)
            if r.get('status') == 'success':
                op_type = ('update_' if r.get('update') else 'add_') + collection
                self.add_op_log(op_type, context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except DbError as error:
            self.send_db_error(error)


class DataDeleteApi(BaseHandler):
    URL = '/api/data/@collection/delete'

    def post(self, collection):
        """ 批量删除 """
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel']
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_id', '_ids'), ]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            if data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(data['_id'])})
                self.add_op_log('delete_%s' % collection, target_id=data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in data['_ids']]}})
                self.add_op_log('delete_%s' % collection, target_id=data['_ids'])
            self.send_data_response(dict(deleted_count=r.deleted_count))

        except DbError as error:
            self.send_db_error(error)


class FetchDataTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@data_task'

    def post(self, data_task):
        """ 批量领取数据任务 """

        def get_tasks():
            # ocr_text任务时，需要把blocks/columns/chars等参数传过去
            if data_task == 'ocr_text':
                pages = self.db.page.find({'name': {'$in': [t['doc_id'] for t in tasks]}})
                pages = {p['name']: dict(blocks=p.get('blocks'), columns=p.get('columns'), chars=p.get('chars'))
                         for p in pages}
                for t in tasks:
                    t['input'] = pages.get(t['doc_id'])
                    if not t['input']:
                        logging.warning('page %s not found' % t['doc_id'])

            return [dict(task_id=str(t['_id']), priority=t.get('priority'), page_name=t.get('doc_id'),
                         input=t.get('input')) for t in tasks]

        try:
            data = self.get_request_data()
            size = int(data.get('size') or 1)

            condition = {'task_type': data_task, 'status': self.STATUS_OPENED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_error_response(errors.no_task_to_pick)

            # 批量获取任务
            update = dict(status=self.STATUS_FETCHED, picked_time=datetime.now(), updated_time=datetime.now(),
                          picked_user_id=self.current_user['_id'], picked_by=self.current_user['name'])
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': update})
            if r.matched_count:
                _tasks = get_tasks()
                self.send_data_response(dict(tasks=_tasks))

        except DbError as err:
            return self.send_db_error(err)


class ConfirmFetchDataTasksApi(TaskHandler):
    URL = '/api/task/confirm_fetch/@data_task'

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
                self.send_error_response(errors.no_object)

        except DbError as err:
            return self.send_db_error(err)


class SubmitDataTasksApi(SubmitDataTaskApi):
    URL = '/api/task/submit/@data_task'

    def post(self, task_type):
        """ 批量提交数据任务。提交参数为tasks，格式如下：
        [
        {'task_type': '', 'ocr_task_id':'', 'task_id':'', 'page_name':'', 'status':'success', 'result':{}},
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
                tasks.append(dict(ocr_task_id=task['ocr_task_id'], task_id=task['task_id'],
                                  status='success' if r is True else 'failed',
                                  page_name=task.get('page_name'), message=r))
            self.send_data_response(dict(tasks=tasks))

        except DbError as err:
            return self.send_db_error(err)
