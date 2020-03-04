#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
from os import path
from bson.objectid import ObjectId
from utils.build_js import build_js
from tornado.escape import to_basestring
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler
from controller.helper import align_code
from controller.data.data import Tripitaka, Reel, Sutra, Volume, Page, Char

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class DataUpsertApi(BaseHandler):
    URL = '/api/data/@metadata'

    def post(self, metadata):
        """ 新增或修改 """
        try:
            model = eval(metadata.capitalize())
            r = model.save_one(self.db, metadata, self.data)
            if r.get('status') == 'success':
                self.add_op_log(('update_' if r.get('update') else 'add_') + metadata, context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except self.DbError as error:
            return self.send_db_error(error)


class DataUploadApi(BaseHandler):
    URL = '/api/data/@metadata/upload'

    def save_error(self, collection, errs):
        data_path = path.join(self.application.BASE_DIR, 'static', 'upload', 'data')
        if not path.exists(data_path):
            os.makedirs(data_path)
        result = 'upload-%s-result-%s.csv' % (collection, self.now().strftime('%Y%m%d%H%M'))
        with open(path.join(data_path, result), 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerows(errs)
        return '/static/upload/data/' + result

    def post(self, collection):
        """ 批量上传 """
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel', 'page']
        model = eval(collection.capitalize())
        upload_file = self.request.files.get('csv') or self.request.files.get('json')
        content = to_basestring(upload_file[0]['body'])
        with StringIO(content) as fn:
            if collection == 'page':
                assert self.data.get('layout'), 'need layout'
                r = Page.insert_many(self.db, file_stream=fn, layout=self.data['layout'])
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


class DataDeleteApi(BaseHandler):
    URL = '/api/data/@metadata/delete'

    def post(self, collection):
        """ 批量删除 """
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_op_log('delete_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_op_log('delete_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class UpdateSourceApi(BaseHandler):
    URL = '/api/data/(page|char)/source'

    def post(self, collection):
        """ 批量更新分类"""
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db[collection].update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_op_log('update_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_op_log('update_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class PageExportCharsApi(BaseHandler):
    URL = '/api/data/page/export_char'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_empty, 'page_names')]
            self.validate(self.data, rules)

            # 启动脚本，生成字表
            page_names = ','.join(self.data['page_names'])
            script = 'nohup python3 export_chars.py --page_name="%s" >> log/cut.log 2>&1 &' % page_names
            os.system(script)

            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class DataGenJsApi(BaseHandler):
    URL = '/api/data/gen_js'

    def post(self):
        """ build_js"""
        try:
            rules = [(v.not_empty, 'collection', 'tripitaka_code')]
            self.validate(self.data, rules)

            if self.data['tripitaka_code'] == '所有':
                build_js(self.db, self.data['collection'])
            else:
                tripitaka = self.db.tripitaka.find_one({'tripitaka_code': self.data['tripitaka_code']})
                if not tripitaka:
                    self.send_error_response(e.no_object, message='藏经不存在')
                elif not tripitaka.get('store_pattern'):
                    self.send_error_response(e.not_allowed_empty, message='存储模式不允许为空')
                build_js(self.db, self.data['collection'], self.data['tripitaka_code'])

            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)
