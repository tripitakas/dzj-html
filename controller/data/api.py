#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import to_basestring
import controller.validate as v
from controller.base import BaseHandler, DbError
from .data import Tripitaka, Volume, Reel, Sutra

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


class PublishTodoPages(BaseHandler):
    # 数据状态表
    STATUS_TODO = 'todo'
    STATUS_FAILED = 'failed'
    STATUS_FINISHED = 'finished'
    status_names = {STATUS_TODO: '排队中', STATUS_FAILED: '失败', STATUS_FINISHED: '已完成'}

    def publish_todo_page(self, page_names, force, data_field):
        """ 发布待办页面。
        :param page_names 待发布的页面
        :param force 页面已完成时，是否重新发布
        :param data_field 更新page表的哪个字段
        :return 格式如下：{'un_existed':[...],  'finished':[...], 'published':[...]}
        """
        assert data_field in ['ocr_status', 'upload_status']

        log = dict()

        # 检查页面是否存在
        pages = list(self.db['page'].find({'name': {'$in': page_names}}))
        log['un_existed'] = set(page_names) - set([page.get('name') for page in pages])
        page_names = [page.get('name') for page in pages]

        # 去掉已完成的页面（如果不重新发布）
        if not force and page_names:
            condition = dict(status=self.STATUS_FINISHED, page_id={'$in': list(page_names)})
            log['finished'] = set(t.get('name') for t in self.db.page.find(condition, {'name': 1}))
            page_names = set(page_names) - log['finished']

        # 设置页面状态
        if page_names:
            update = {data_field: self.STATUS_TODO, 'updated_time': datetime.now()}
            self.db.page.update_many({'name': {'$in': list(page_names)}}, {'$set': update})
            log['published'] = page_names

        return {k: value for k, value in log.items() if value}

    @classmethod
    def get_status_name(cls, status):
        return cls.status_names.get(status)

    def get_doc_ids(self, data):
        doc_ids = data.get('doc_ids')
        if not doc_ids:
            ids_file = self.request.files.get('ids_file')
            if ids_file:
                ids_str = str(ids_file[0]['body'], encoding='utf-8').strip('\n') if ids_file else ''
                ids_str = re.sub(r'\n+', '|', ids_str)
                doc_ids = ids_str.split(r'|')
            elif data.get('prefix'):
                condition = {'name': {'$regex': '.*%s.*' % data['prefix'], '$options': '$i'}}
                doc_ids = [doc.get('name') for doc in self.db.page.find(condition)]
        return doc_ids

    def publish(self, data_field):
        data = self.get_request_data()
        data['doc_ids'] = self.get_doc_ids(data)
        rules = [(v.not_empty, 'doc_ids', 'force')]
        err = v.validate(data, rules)
        if err:
            return self.send_error_response(err)

        try:
            assert isinstance(data['doc_ids'], list)
            force = data['force'] == '1'
            log = self.publish_todo_page(data['doc_ids'], force, data_field)
            return self.send_data_response({k: value for k, value in log.items() if value})

        except DbError as err:
            return self.send_db_error(err)


class PublishOcrApi(PublishTodoPages):
    URL = '/api/data/publish_ocr'

    def post(self):
        """ 发布待OCR的页面。"""
        self.publish('ocr_status')


class UploadCloudApi(PublishTodoPages):
    URL = '/api/data/upload_cloud'

    def post(self):
        """ 发布待OCR的页面。"""
        self.publish('upload_status')
