#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import to_basestring
import controller.validate as v
from controller import errors
from controller.base import BaseHandler, DbError
from .data import Tripitaka, Volume, Reel, Sutra
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
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel']
        collection_class = eval(collection.capitalize())
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            r = collection_class.save_many(self.db, collection, file_stream=fn)
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
                self.add_op_log('delete_%s' % collection, target_id=str(data['_id']))
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in data['_ids']]}})
                self.add_op_log('delete_%s' % collection, target_id=str(data['_ids']))
            self.send_data_response(dict(deleted_count=r.deleted_count))

        except DbError as error:
            self.send_db_error(error)


class PickDataTasksApi(TaskHandler):
    URL = '/api/task/pick_many/@data_task'

    def post(self, data_task):
        """ 批量领取数据任务 """
        try:
            data = self.get_request_data()
            size = int(data.get('size') or 1)

            condition = {'task_type': data_task, 'status': self.STATUS_OPENED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_error_response(errors.no_task_to_pick)

            # 批量分配任务
            update = dict(status=self.STATUS_PICKED, picked_time=datetime.now(), updated_time=datetime.now(),
                          picked_user_id=self.current_user['_id'], picked_by=self.current_user['name'])
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': update})
            if r.modified_count:
                self.send_data_response([dict(task_id=str(t['_id']), page_name=t['doc_id']) for t in tasks])

        except DbError as err:
            return self.send_db_error(err)


class SubmitDataTasksApi(SubmitDataTaskApi):
    URL = '/api/task/submit/@data_task'

    def post(self, task_type):
        """ 批量提交数据任务。提交格式如下：
        {'tasks':[
            {'task_type': '', 'task_id':'', 'status':'success', 'page':{}, ...},
            {'task_type': '', 'task_id':'', 'status':'failed', 'message':''},
        ]}
        其中，task_id是任务id，status为success/failed，page是成功时的页面数据，...表示其它数据内容，message为失败时的错误信息。
        """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            ret = []
            for task in data['tasks']:
                r = self.submit_one(task) if task['task_type'] == task_type else '任务类型不一致'
                ret.append(dict(task_id=task['task_id'], status='success' if r is True else 'failed', message=r))
            self.send_data_response(ret)

        except DbError as err:
            return self.send_db_error(err)
