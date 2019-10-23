#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import to_basestring
import controller.validate as v
from controller import errors
from controller.base import BaseHandler, DbError
from .data import Tripitaka, Volume, Reel, Sutra
from .base import DataHandler

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


class DataAddOrUpdateApi(BaseHandler, Tripitaka):
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


class GetReadyPagesApi(BaseHandler):
    URL = '/api/data/pages'

    def post(self):
        """获取page页面列表"""
        try:
            data = self.get_request_data()
            doc_filter = dict()
            if data.get('prefix'):
                doc_filter.update({'$regex': '.*%s.*' % data.get('prefix'), '$options': '$i'})
            if data.get('exclude'):
                doc_filter.update({'$nin': data.get('exclude')})
            condition = {'name': doc_filter} if doc_filter else {}
            page_no = int(data.get('page', 0)) if int(data.get('page', 0)) > 1 else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db.page.count_documents(condition)
            docs = self.db.page.find(condition).limit(page_size).skip(page_size * (page_no - 1))
            response = {'docs': [d['name'] for d in list(docs)], 'page_size': page_size,
                        'page_no': page_no, 'total_count': count}
            return self.send_data_response(response)
        except DbError as err:
            return self.send_db_error(err)


class PublishPageTaskApi(DataHandler):
    URL = '/api/data/publish/(ocr|upload_cloud)'

    def post(self, data_task):
        """ 发布页面数据任务。"""
        try:
            self.publish(data_task)
        except DbError as err:
            return self.send_db_error(err)


class PublishImportImagesApi(DataHandler):
    URL = '/api/data/publish/import_image'

    def post(self):
        """ 发布图片导入任务"""

        def get_item():
            item = {k: data.get(k) or '' for k in ['dir', 'redo', 'remark']}
            item['redo'] = item['redo'] == '1'
            item.update(dict(
                status=self.STATUS_TODO, create_time=datetime.now(), updated_time=datetime.now(),
                publish_user_id=self.current_user['_id'], publish_by=self.current_user['name']
            ))
            return item

        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'dir', 'redo')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            self.db['import'].insert_one(get_item())

            self.send_data_response()
            self.add_op_log('publish_import_image_task', context='%s,%s' % (data['dir'], data['redo']))
        except DbError as err:
            return self.send_db_error(err)


class PickPageTasksApi(DataHandler):
    URL = '/api/data/pick/(ocr|upload_cloud)'

    def post(self, data_task):
        """ 领取待办数据（OCR、上传云图）任务 """
        try:
            data = self.get_request_data()
            size = int(data.get('size') or 1)
            condition = {'tasks.%s.status' % data_task: self.STATUS_TODO}
            pages = list(self.db.page.find(condition).limit(size))
            if not pages:
                self.send_error_response(errors.no_object)

            page_names = [p['name'] for p in pages]
            update = dict(status=self.STATUS_PICKED, picked_time=datetime.now(), updated_time=datetime.now(),
                          picked_user_id=self.current_user['_id'], picked_by=self.current_user['name'])
            self.db.page.update_many({'name': {'$in': page_names}}, {'$set': update})

            self.send_data_response(page_names)
        except DbError as err:
            return self.send_db_error(err)


class PickImportImagesApi(DataHandler):
    URL = '/api/data/pick/import_image'

    def post(self):
        """ 领取待办导入图片任务 """
        try:
            task = self.db['import'].find_one({'status': self.STATUS_TODO})
            if not task:
                self.send_error_response(errors.no_object)

            update = dict(status=self.STATUS_PICKED, picked_time=datetime.now(), updated_time=datetime.now(),
                          picked_user_id=self.current_user['_id'], picked_by=self.current_user['name'])
            self.db['import'].update_one({'_id': task['_id']}, {'$set': update})

            self.send_data_response(task)
        except DbError as err:
            return self.send_db_error(err)


class SubmitOcrApi(DataHandler):
    URL = '/api/data/submit/ocr'

    def post(self):
        """ 批量提交OCR结果
        提交格式：{'result':[{'name':'name1', 'blocks':[], }, {'name':'name2',}....]}"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'result')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            pre = 'tasks.ocr.'
            for page in data['result']:
                if page.get('chars'):
                    update = {pre + 'status': self.STATUS_FINISHED, pre + 'finished_time': datetime.now(),
                              pre + 'updated_time': datetime.now()}
                    for field in ['blocks', 'columns', 'chars', 'ocr']:
                        if data.get(field):
                            update[field] = data[field]
                else:
                    update = {pre + 'status': self.STATUS_FAILED, pre + 'updated_time': datetime.now(),
                              pre + 'message': page.get('message')}
                self.db.page.update_one({'name': page['name']}, {'$set': update})

            self.send_data_response()
        except DbError as err:
            return self.send_db_error(err)


class SubmitUploadCloudApi(DataHandler):
    URL = '/api/data/submit/upload_cloud'

    def post(self):
        """ 批量提交上传云图的结果
        提交格式：{'result':[{'name':'name1', status: 'success', message: ''}, {'name':'name2',}....]}
        """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'result')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            pre = 'tasks.upload_cloud.'
            for page in data['result']:
                status = self.STATUS_FINISHED if page['status'] == 'success' else self.STATUS_FAILED
                update = {pre + 'status': status, pre + 'message': data.get('message'),
                          pre + 'finished_time': datetime.now(), pre + 'updated_time': datetime.now()}
                self.db.page.update_one({'name': page['name']}, {'$set': update})

            self.send_data_response()
        except DbError as err:
            return self.send_db_error(err)


class SubmitImportImagesApi(DataHandler):
    URL = '/api/data/submit/import_image'

    def post(self):
        """ 提交导入图片任务 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, '_id', 'status'), (v.exist, self.db['import'], '_id')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            status = self.STATUS_FINISHED if data['status'] == 'success' else self.STATUS_FAILED
            update = {'status': status, 'finished_time': datetime.now(), 'updated_time': datetime.now(),
                      'remark': data.get('message')}
            self.db['import'].update_one({'_id': ObjectId(data['_id'])}, {'$set': update})
            self.send_data_response()

        except DbError as err:
            return self.send_db_error(err)


class DeleteImportImagesApi(DataHandler):
    URL = '/api/data/delete/import_image'

    def post(self):
        """ 删除导入图片任务 """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, '_id'), (v.exist, self.db['import'], '_id')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            self.db['import'].delete_one({'_id': ObjectId(data['_id'])})
            self.send_data_response()

        except DbError as err:
            return self.send_db_error(err)
