#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import csv
import shutil
from os import path
from bson.objectid import ObjectId
from tornado.escape import to_basestring
from controller import auth as a
from controller import errors as e
from controller import helper as h
from controller import validate as v
from controller.base import BaseHandler
from controller.data.data import Variant
from controller.task.base import TaskHandler
from controller.data.data import Tripitaka, Reel, Sutra, Volume

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class PublishImportImageApi(TaskHandler):
    URL = r'/api/publish/import_image'

    def post(self):
        """发布图片导入任务"""
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


class DataUpsertApi(BaseHandler):
    URL = '/api/data/@metadata'

    def post(self, metadata):
        """新增或修改"""
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
        """批量上传"""
        assert collection in ['tripitaka', 'volume', 'sutra', 'reel', 'page']
        model = eval(collection.capitalize())
        upload_file = self.request.files.get('csv')
        try:
            content = to_basestring(upload_file[0]['body'])
        except UnicodeDecodeError:
            content = upload_file[0]['body'].decode('gbk')
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
        """批量删除"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db[collection].delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_log('delete_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_log('delete_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except self.DbError as error:
            return self.send_db_error(error)


class VariantUpsertApi(BaseHandler, Variant):
    URL = '/api/variant/upsert'

    def post(self):
        """新增/更新异体字"""
        try:
            rules = [(v.not_both_empty, 'img_name', 'txt'), (v.not_both_empty, 'nor_txt', 'user_txt')]
            self.validate(self.data, rules)

            doc = self.pack_doc(self.data, exclude_none=False)
            doc['nor_txt'] = doc.get('nor_txt') or doc.get('user_txt')
            if doc.get('_id'):  # 更新
                vt = self.db.variant.find_one({'_id': doc['_id']})
                if not vt:
                    return self.send_error_response(e.no_object, message='没有找到异体字')
                doc.pop('uid', 0)  # 不能更新uid
                doc.pop('v_code', 0)  # 不能更新v_code
                doc['updated_time'] = self.now()
                if doc['nor_txt'] and doc['nor_txt'] != vt.get('nor_txt'):
                    doc['nor_txt'] = self.recurse_nor_txt(doc['nor_txt'])
                if vt.get('v_code') and doc.get('img_name') != vt.get('img_name'):  # 更新图片
                    self.update_variant_img(doc['img_name'], vt['v_code'])
                self.db.variant.update_one({'_id': doc['_id']}, {'$set': doc})
                self.send_data_response()
                return self.add_log('update_variant', target_id=doc['_id'])

            if re.match(r'^[0-9a-zA-Z_]+$', doc.get('txt') or ''):
                doc['img_name'] = doc.pop('txt').strip()
            if doc.get('img_name'):  # 图片字
                if self.db.variant.find_one({'img_name': doc['img_name']}):
                    return self.send_error_response(e.variant_exist, message='异体字图%s已存在' % doc['img_name'])
                doc['uid'], doc['v_code'] = self.get_next_code()
                self.update_variant_img(doc['img_name'], doc['v_code'])
            else:  # 文字
                if self.db.variant.find_one({'txt': doc['txt']}):
                    return self.send_error_response(e.variant_exist, message='异体字%s已存在' % doc['txt'])
            doc['nor_txt'] = self.recurse_nor_txt(doc['nor_txt'])
            doc.update(dict(create_user_id=self.user_id, create_by=self.username, create_time=self.now()))
            r = self.db.variant.insert_one(doc)
            self.send_data_response(dict(id=r.inserted_id, v_code=doc.get('v_code')))
            self.add_log('add_variant', target_id=r.inserted_id, target_name=doc.get('img_name') or doc.get('txt'))

        except self.DbError as error:
            return self.send_db_error(error)

    def update_variant_img(self, img_name, v_code):
        src_url = self.get_web_img(img_name, 'char')
        src_fn = 'static/img/' + src_url[src_url.index('chars'):]
        dst_fn = 'static/img/variants/%s.jpg' % v_code
        try:
            shutil.copy(path.join(h.BASE_DIR, src_fn), path.join(h.BASE_DIR, dst_fn))
        except Exception as err:
            self.send_error_response(e.no_object, message=str(err))

    def recurse_nor_txt(self, nor_txt):
        cond = {'v_code': nor_txt} if nor_txt[0] == 'v' else {'txt': nor_txt}
        vt = self.db.variant.find_one(cond, {'nor_txt': 1})
        return vt and vt.get('nor_txt') or nor_txt

    def get_next_code(self):
        max_uid = self.db.variant.find_one({'uid': {'$ne': None}}, sort=[('uid', -1)])
        next_uid = int(max_uid['uid']) + 1 if max_uid else 1
        v_code = 'v' + h.dec2code36(next_uid)
        if self.db.char.find_one({'txt': v_code}):  # 下一个code已被使用
            return self.send_error_response(e.variant_exist, message='编号已错乱，请联系管理员！')
        return next_uid, v_code


class VariantDeleteApi(BaseHandler):
    URL = '/api/variant/delete'

    def post(self):
        """用户删除图片异体字"""

        try:
            if self.data.get('v_code'):
                if self.db.char.find_one({'txt': self.data['v_code']}):
                    return self.send_error_response(e.unauthorized, message='不能删除使用中的异体字')
                r = self.db.variant.delete_one({'v_code': self.data['v_code']})
                if not r.deleted_count:
                    return self.send_error_response(e.no_object, message='没有找到异体字%s' % self.data['v_code'])
                self.send_data_response(dict(count=r.deleted_count))
                self.add_log('delete_variant', target_name=self.data['v_code'])
            elif self.data.get('_id'):
                vt = self.db.variant.find_one({'_id': ObjectId(self.data['_id'])}, {'v_code': 1})
                if vt.get('v_code') and self.db.char.find_one({'txt': vt['v_code']}):
                    return self.send_error_response(e.unauthorized, message='不能删除使用中的图片异体字')
                r = self.db.variant.delete_one({'_id': ObjectId(self.data['_id'])})
                self.send_data_response(dict(count=r.deleted_count))
                self.add_log('delete_variant', target_id=self.data['_id'])
            elif self.data.get('_ids'):
                deleted, un_deleted = [], []
                vts = list(self.db.variant.find({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}))
                for vt in vts:
                    if not vt.get('v_code') or not self.db.char.find_one({'txt': vt['v_code']}):
                        deleted.append(str(vt['_id']))
                    else:
                        un_deleted.append(str(vt['_id']))
                if not deleted:
                    return self.send_error_response(e.unauthorized, message='所有异体字均被使用中，不能删除')
                r = self.db.variant.delete_many({'_id': {'$in': [ObjectId(i) for i in deleted]}})
                self.send_data_response(dict(deleted=deleted, un_deleted=un_deleted, count=r.deleted_count))
                self.add_log('delete_variant', target_id=deleted)

        except self.DbError as error:
            return self.send_db_error(error)


class VariantMergeApi(BaseHandler):
    URL = '/api/variant/merge'

    def post(self):
        """合并图片异体字"""
        try:
            rules = [(v.not_empty, 'v_codes', 'main_code')]
            self.validate(self.data, rules)

            assert self.data['main_code'] in self.data['v_codes']
            sub_codes = [code for code in self.data['v_codes'] if code != self.data['main_code']]
            if not sub_codes:
                return self.send_error_response(e.no_object, message='没有找到待合并的编码')

            self.db.char.update_many({'txt': {'$in': sub_codes}}, {'$set': {'txt': self.data['main_code']}})
            r = self.db.variant.delete_many({'v_code': {'$in': sub_codes}})
            self.send_data_response(dict(count=r.deleted_count))
            self.add_log('merge_variant', target_name=sub_codes, content='merge to ' + self.data['main'])

        except self.DbError as error:
            return self.send_db_error(error)


class VariantSourceApi(BaseHandler):
    URL = '/api/variant/source'

    def post(self):
        """ 更新分类"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids'), (v.not_empty, 'source')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db.variant.update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_log('update_variant', target_id=self.data['_id'])
            else:
                r = self.db.variant.update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_log('update_variant', target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class VariantCode2NorTxtApi(BaseHandler):
    URL = '/api/variant/code2nor'

    def post(self):
        """ 获取所属正字"""
        try:
            rules = [(v.not_empty, 'codes')]
            self.validate(self.data, rules)
            vts = list(self.db.variant.find({'v_code': {'$in': self.data['codes']}}, {'v_code': 1, 'nor_txt': 1}))
            self.send_data_response(dict(code2nor={vt['v_code']: vt['nor_txt'] for vt in vts if vt.get('nor_txt')}))

        except self.DbError as error:
            return self.send_db_error(error)
