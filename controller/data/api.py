#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import csv
import logging
from os import path
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from utils.build_js import build_js
from controller import errors
from controller import validate as v
from controller.base import BaseHandler, DbError
from controller.task.base import TaskHandler
from controller.data.submit import SubmitDataTaskApi
from controller.data.data import Tripitaka, Reel, Sutra, Volume, Page

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class DataUploadApi(BaseHandler):
    URL = '/api/data/@metadata/upload'

    def save_error(self, collection, errs):
        data_path = path.join(self.application.BASE_DIR, 'static', 'upload', 'data')
        if not path.exists(data_path):
            os.makedirs(data_path)
        result = 'upload-%s-result-%s.csv' % (collection, datetime.now().strftime('%Y%m%d%H%M'))
        with open(path.join(data_path, result), 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerows(errs)
        return '/static/upload/data/' + result

    def post(self, collection):
        """ 批量上传 """
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel', 'page']
        data = self.get_request_data()
        model = eval(collection.capitalize())
        upload_file = self.request.files.get('csv') or self.request.files.get('json')
        content = to_basestring(upload_file[0]['body'])
        with StringIO(content) as fn:
            if collection == 'page':
                assert data.get('layout'), 'need layout'
                r = Page.insert_many(self.db, file_stream=fn, layout=data['layout'])
            else:
                update = False if collection == 'tripitaka' else True
                r = model.save_many(self.db, collection, file_stream=fn, update=update)

            if r.get('status') == 'success':
                if r.get('errors'):
                    r['url'] = self.save_error(collection, r.get('errors'))
                self.send_data_response(r)
                self.add_op_log('upload_%s' % collection, context=r.get('message'))
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class DataAddOrUpdateApi(BaseHandler):
    URL = '/api/data/@metadata'

    def post(self, metadata):
        """ 新增或修改 """
        model = eval(metadata.capitalize())
        try:
            data = self.get_request_data()
            if metadata == 'page':
                if data.get('level-box'):
                    data['level.box'] = data['level-box']
                if data.get('level-text'):
                    data['level.text'] = data['level-text']
            r = model.save_one(self.db, metadata, data)
            if r.get('status') == 'success':
                self.add_op_log(('update_' if r.get('update') else 'add_') + metadata, context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except DbError as error:
            return self.send_db_error(error)


class DataDeleteApi(BaseHandler):
    URL = '/api/data/@metadata/delete'

    def post(self, collection):
        """ 批量删除 """
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_id', '_ids')]
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
            return self.send_db_error(error)


class DataPageUpdateSourceApi(BaseHandler):
    URL = '/api/data/page/source'

    def post(self):
        """ 批量更新分类 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            if data.get('_id'):
                r = self.db.page.update_one({'_id': ObjectId(data['_id'])}, {'$set': {'source': data['source']}})
                self.add_op_log('update_page_source', target_id=data['_id'])
            else:
                r = self.db.page.update_many({'_id': {'$in': [ObjectId(i) for i in data['_ids']]}},
                                             {'$set': {'source': data['source']}})
                self.add_op_log('update_page_source', target_id=data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except DbError as error:
            return self.send_db_error(error)


class DataGenJsApi(BaseHandler):
    URL = '/api/data/gen_js'

    def post(self):
        """ 生成册信息 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'collection', 'tripitaka_code')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            if data['tripitaka_code'] == '所有':
                build_js(self.db, data['collection'])
            else:
                tripitaka = self.db.tripitaka.find_one({'tripitaka_code': data['tripitaka_code']})
                if not tripitaka:
                    self.send_error_response(errors.no_object, message='藏经不存在')
                elif not tripitaka.get('store_pattern'):
                    self.send_error_response(errors.not_allowed_empty, message='存储模式不允许为空')
                build_js(self.db, data['collection'], data['tripitaka_code'])

            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class FetchDataTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@data_task'

    def post(self, data_task):
        """ 批量领取数据任务 """

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

        except DbError as error:
            return self.send_db_error(error)


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
                message = '' if r is True else r
                status = 'success' if r is True else 'failed'
                tasks.append(dict(ocr_task_id=task['ocr_task_id'], task_id=task['task_id'], status=status,
                                  page_name=task.get('page_name'), message=message))
            self.send_data_response(dict(tasks=tasks))

        except DbError as error:
            return self.send_db_error(error)
