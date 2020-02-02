#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import csv
from os import path
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from utils.build_js import build_js
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler, DbError
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
                self.add_op_log('upload_' + collection, context=r.get('message'))
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class DataAddOrUpdateApi(BaseHandler):
    URL = '/api/data/@metadata'

    def post(self, metadata):
        """ 新增或修改 """
        model = eval(metadata.capitalize())
        try:
            data = self.get_request_data()
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
                self.add_op_log('delete_' + collection, target_id=data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in data['_ids']]}})
                self.add_op_log('delete_' + collection, target_id=data['_ids'])
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
                self.add_op_log('update_page', target_id=data['_id'])
            else:
                r = self.db.page.update_many({'_id': {'$in': [ObjectId(i) for i in data['_ids']]}},
                                             {'$set': {'source': data['source']}})
                self.add_op_log('update_page', target_id=data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except DbError as error:
            return self.send_db_error(error)


class DataGenJsApi(BaseHandler):
    URL = '/api/data/gen_js'

    def post(self):
        """ build_js"""
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
                    self.send_error_response(e.no_object, message='藏经不存在')
                elif not tripitaka.get('store_pattern'):
                    self.send_error_response(e.not_allowed_empty, message='存储模式不允许为空')
                build_js(self.db, data['collection'], data['tripitaka_code'])

            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)
