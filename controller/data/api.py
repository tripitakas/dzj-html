#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import csv
from os import path
from bson.objectid import ObjectId
from utils.build_js import build_js
from tornado.escape import to_basestring
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler
from controller.task.base import TaskHandler
from controller.data.data import Tripitaka, Reel, Sutra, Volume, Variant

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
            r = model.save_one(self.db, metadata, self.data, self=self)
            if r.get('status') == 'success':
                self.send_data_response(r)
                self.add_log(('update_' if r.get('update') else 'add_') + metadata, target_id=r.get('id'))
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
        upload_file = self.request.files.get('csv')
        content = to_basestring(upload_file[0]['body'])
        with StringIO(content) as fn:
            update = False if collection == 'tripitaka' else True
            r = model.save_many(self.db, collection, file_stream=fn, update=update)
            if r.get('status') == 'success':
                if r.get('errors'):
                    r['url'] = self.save_error(collection, r.get('errors'))
                self.send_data_response(r)
                self.add_log('upload_' + collection, target_name=r.get('target_names'), content=r.get('message'))
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class DataDeleteApi(BaseHandler):
    URL = '/api/data/@metadata/delete'

    def post(self, collection):
        """ 批量删除 """

        def pre_variant():
            if self.data.get('_id'):
                vt = self.db.variant.find_one({'_id': ObjectId(self.data['_id'])})
                if self.db.char.find_one({'txt': 'Y%s' % vt['uid'] if vt.get('uid') else vt['txt']}):
                    return self.send_error_response(e.unauthorized, message='不能删除使用中的异体字')
            else:
                can_delete = []
                vts = list(self.db.variant.find({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}))
                for vt in vts:
                    if not self.db.char.find_one({'txt': 'Y%s' % vt['uid'] if vt.get('uid') else vt['txt']}):
                        can_delete.append(str(vt['_id']))
                if can_delete:
                    self.data['_ids'] = can_delete
                else:
                    return self.send_error_response(e.unauthorized, message='所有异体字均被使用中，不能删除')

        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if collection == 'variant':
                pre_variant()

            if self.data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_log('delete_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_log('delete_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class VariantDeleteApi(BaseHandler):
    URL = '/api/variant/delete'

    def post(self):
        """ 删除图片异体字"""
        try:
            rules = [(v.not_empty, 'uid'), (v.is_char_uid, 'uid')]
            self.validate(self.data, rules)
            uid = self.data['uid']
            if self.db.char.find_one({'txt': uid}):
                return self.send_error_response(e.unauthorized, message='不能删除使用中的异体字')
            vt = self.db.variant.find_one({'uid': int(uid.strip('Y'))})
            if not vt:
                return self.send_error_response(e.no_object, message='没有找到%s相关的异体字' % uid)
            self.db.variant.delete_one({'_id': vt['_id']})
            self.send_data_response()
            self.add_log('delete_variant', target_id=vt['_id'])

        except self.DbError as error:
            return self.send_db_error(error)


class VariantMergeApi(BaseHandler):
    URL = '/api/variant/merge'

    def post(self):
        """ 合并图片异体字"""
        try:
            rules = [(v.not_empty, 'img_names', 'main')]
            self.validate(self.data, rules)
            assert self.data['main'] in self.data['img_names']
            # 更新字数据
            names2merge = [name for name in self.data['img_names'] if name != self.data['main']]
            self.db.char.update_many({'txt': {'$in': names2merge}}, {'$set': {'txt': self.data['main']}})
            # 删除异体字图
            self.db.variant.delete_many({'img_name': {'$in': names2merge}})
            self.send_data_response()
            self.add_log('merge_variant', target_name=names2merge, content='merge to ' + self.data['main'])

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


class PublishImportImageApi(TaskHandler):
    URL = r'/api/publish/import_image'

    def post(self):
        """ 发布图片导入任务"""
        try:
            rules = [(v.not_empty, 'source', 'import_dir', 'priority', 'redo', 'layout')]
            self.validate(self.data, rules)

            task = self.get_publish_meta('import_image')
            params = {k: self.data.get(k) for k in ['source', 'pan_name', 'import_dir', 'layout', 'redo']}
            task.update(dict(status=self.STATUS_PUBLISHED, priority=int(self.data['priority']), params=params))
            r = self.db.task.insert_one(task)
            message = '%s, %s,%s' % ('import_image', self.data['import_dir'], self.data['redo'])
            self.add_log('publish_task', target_id=r.inserted_id, content=message)
            self.send_data_response(dict(_id=r.inserted_id))

        except self.DbError as error:
            return self.send_db_error(error)
