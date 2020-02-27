#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import csv
import json
from os import path
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from utils.build_js import build_js
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler, DbError
from controller.data.data import Tripitaka, Reel, Sutra, Volume, Page, Char

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


class DataAddOrUpdateApi(BaseHandler):
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

        except DbError as error:
            return self.send_db_error(error)


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

        except DbError as error:
            return self.send_db_error(error)


class DataPageUpdateSourceApi(BaseHandler):
    URL = '/api/data/page/source'

    def post(self):
        """ 批量更新分类 """
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.page.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_op_log('update_page', target_id=self.data['_id'])
            else:
                r = self.db.page.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_op_log('update_page', target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except DbError as error:
            return self.send_db_error(error)


class DataPageExportCharApi(BaseHandler):
    URL = '/api/data/page/export_char'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            chars = []
            invalid_pages = []
            invalid_chars = []
            project = {'name': 1, 'chars': 1, 'columns': 1, 'source': 1}
            _ids = [self.data['_id']] if self.data.get('_id') else self.data['_ids']
            pages = self.db.page.find({'_id': {'$in': [ObjectId(i) for i in _ids]}}, project)
            for p in pages:
                self.export_chars(p, chars, invalid_chars, invalid_pages)
            # 插入数据库，忽略错误
            r = self.db.char.insert_many(chars, ordered=False)
            inserted_chars = [c['_id'] for c in list(self.db.char.find({'_id': {'$in': r.inserted_ids}}))]
            # 未插入的数据，进行更新
            un_inserted_chars = [c for c in chars if c['_id'] not in inserted_chars]
            for c in un_inserted_chars:
                self.db.char.update_one({'_id': c['_id']}, {'$set': {'pos': c['pos']}})

            self.send_data_response(inserted_count=len(chars), invalid_pages=invalid_pages, invalid_chars=invalid_chars)

        except DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def export_chars(p, chars, invalid_chars, invalid_pages):
        try:
            col2cid = {cl['column_id']: cl['cid'] for cl in p['columns']}
            for c in p.get('chars', []):
                try:
                    char_id = '%s_%s' % (p['name'], c['cid'])
                    char_code = Page.name2code(char_id)
                    txt = c.get('txt') or c.get('ocr_txt')
                    pos = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                    column_cid = col2cid.get('b%sc%s' % (c['block_no'], c['column_no']))
                    c = {
                        'page_name': p['name'], 'cid': c['cid'], 'char_id': char_id, 'char_code': char_code,
                        'column_cid': column_cid, 'source': p.get('source'), 'has_img': None,
                        'ocr': c['ocr_txt'], 'txt': txt, 'cc': c.get('cc'),
                        'sc': c.get('sc'), 'pos': pos,
                    }
                    chars.append(c)
                except KeyError:
                    invalid_chars.append(c)
        except KeyError:
            invalid_pages.append(p)


class DataCharUpdateSourceApi(BaseHandler):
    URL = '/api/data/char/source'

    def post(self):
        """ 批量更新分类 """
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.char.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_op_log('update_char', target_id=self.data['_id'])
            else:
                r = self.db.char.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_op_log('update_char', target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except DbError as error:
            return self.send_db_error(error)


class DataCharGenImgApi(BaseHandler, Char):
    URL = '/api/data/char/gen_img'

    def post(self):
        """ 批量生成字图 """
        try:
            rules = [(v.not_empty, 'type'), (v.not_both_empty, 'search', '_ids')]
            self.validate(self.data, rules)

            if self.data['type'] == 'selected':
                condition = {'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}
            else:
                condition = self.get_char_search_condition(self.data['search'])[0]

            self.db.char.update_many(condition, {'$set': {'img_need_updated': True}})

            # 启动脚本，生成字图
            script = ['python3', path.join(self.application.BASE_DIR, 'utils', 'extract_cut_img.py')]
            os.system(' '.join(script))

            self.send_data_response()

        except DbError as error:
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

        except DbError as error:
            return self.send_db_error(error)
