#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import csv
import json
from bson import objectid
import controller.errors as e
import controller.validate as v
from functools import cmp_to_key
from tornado.escape import to_basestring
from controller.helper import cmp_page_code
from controller.base import BaseHandler, DbError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Volume(object):
    fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_page_count', 'content_pages',
              'front_cover_pages', 'back_cover_pages', 'remark']
    field_names = {
        'tripitaka_code': '藏编码', 'volume_code': '册编码', 'envelop_no': '函序号', 'volume_no': '册序号',
        'content_page_count': '正文页数', 'content_pages': '正文页', 'front_cover_pages': '封面页',
        'back_cover_pages': '封底页', 'remark': '备注',
    }

    @classmethod
    def get_name_field(cls, name):
        if re.match(r'[0-9a-zA-Z_]+', name):
            return name
        for k, v in cls.field_names.items():
            if name == v:
                return k

    @classmethod
    def get_field_name(cls, field):
        return cls.field_names.get(field, field)

    @classmethod
    def get_item(cls, item):
        for k in list(item.keys()):
            if k not in cls.fields + ['_id']:
                item.pop(k, 0)
        if item.get('_id'):
            if isinstance(item.get('_id'), str):
                item['_id'] = objectid.ObjectId(item.get('_id'))
        else:
            item.pop('_id', 0)

        if item.get('content_pages') and isinstance(item.get('content_pages'), str):
            content_pages = json.loads(item['content_pages'].replace("'", '"'))
            content_pages.sort(key=cmp_to_key(cmp_page_code))
            item['content_pages'] = content_pages

        item['content_page_count'] = len(item['content_pages'])

        if item.get('front_cover_pages') and isinstance(item.get('front_cover_pages'), str):
            front_cover_pages = json.loads(item['front_cover_pages'].replace("'", '"'))
            front_cover_pages.sort(key=cmp_to_key(cmp_page_code))
            item['front_cover_pages'] = front_cover_pages

        if item.get('back_cover_pages') and isinstance(item.get('back_cover_pages'), str):
            back_cover_pages = json.loads(item['back_cover_pages'].replace("'", '"'))
            back_cover_pages.sort(key=cmp_to_key(cmp_page_code))
            item['back_cover_pages'] = back_cover_pages

        return item

    @classmethod
    def validate(cls, item):
        assert isinstance(item, dict)
        rules = [
            (v.not_empty, 'volume_code', 'tripitaka_code', 'volume_no'),
            (v.is_tripitaka, 'tripitaka_code'),
            (v.is_volume, 'volume_code'),
            (v.is_digit, 'volume_no'),
        ]
        err = v.validate(item, rules)
        return err

    @classmethod
    def save_one(cls, db, item):
        item = cls.get_item(item)
        err = cls.validate(item)
        if err:
            return dict(status='failed', errors=err)

        if item.get('_id'):  # 更新
            data = db.volume.find_one({'_id': objectid.ObjectId(item.get('_id'))})
            if data:
                db.volume.update_one({'_id': item.get('_id')}, {'$set': item})
                return dict(status='success', id=item.get('_id'), update=True, insert=False)
            else:
                return dict(status='failed', errors=e.tptk_id_not_existed)
        else:  # 新增
            if not db.volume.find_one({'volume_code': item.get('volume_code')}):
                r = db.volume.insert_one(item)
                return dict(status='success', id=r.inserted_id, update=False, insert=True)
            else:
                return dict(status='failed', errors=e.tptk_code_existed)

    @classmethod
    def save_many(cls, db, items=None, file_stream=None, check_existed=True):
        """ 批量插入或更新数据
        :param db 数据库连接
        :param items 待插入的数据。
        :param file_stream 已打开的文件流。items不为空时，将忽略这个字段。
        :param check_existed 插入前是否检查数据库
        :return {status: 'success'/'failed', code: '',  message: '...', errors:[]}
        """
        if not items and file_stream:
            rows = list(csv.reader(file_stream))
            heads = [cls.get_name_field(r) for r in rows[0]]
            need_fields = [cls.get_field_name(r) for r in cls.fields if r not in heads]
            if need_fields:
                return dict(status='failed', code=e.tptk_field_error[0],
                            message='缺以下字段：%s' % ','.join(need_fields))
            items = [{heads[i]: item for i, item in enumerate(row)} for row in rows[1:]]

        valid_items, valid_codes, error_codes = [], [], []
        for i, item in enumerate(items):
            err = cls.validate(item)
            if err:
                error_codes.append([item.get('volume_code'), err])
            elif item.get('volume_code') in valid_codes:
                error_codes.append([item.get('volume_code'), e.tptk_code_duplicated])
            else:
                valid_items.append(cls.get_item(item))
                valid_codes.append(item.get('volume_code'))

        existed_code = []
        if check_existed:
            existed_record = list(db.volume.find({'volume_code': {'$in': valid_codes}}))
            existed_code = [i.get('volume_code') for i in existed_record]
            existed_items = [i for i in valid_items if i.get('volume_code') in existed_code]
            valid_items = [i for i in valid_items if i.get('volume_code') not in existed_code]
            for item in existed_items:
                db.volume.update_one({'volume_code': item.get('volume_code')}, {'$set': item})

        if valid_items:
            db.volume.insert_many(valid_items)

        error_tip = ('：' + ','.join([i[0] for i in error_codes])) if error_codes else ''
        message = '总共%s条记录，插入%s条，更新%s条，%s条无效数据%s。' % (
            len(items), len(valid_items), len(existed_code), len(error_codes), error_tip)
        return dict(status='success', errors=error_codes, message=message)


class VolumeUploadApi(BaseHandler, Volume):
    URL = '/api/data/volume/upload'

    def post(self):
        """ 批量上传藏数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            r = self.save_many(self.db, file_stream=fn)
            if r.get('status') == 'success':
                self.add_op_log('upload_volume', context=r.get('message'))
                self.send_data_response({'message': r.get('message'), 'errors': r.get('errors')})
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class VolumeAddOrUpdateApi(BaseHandler, Volume):
    URL = '/api/data/volume'

    def post(self):
        """ 新增或修改 """
        try:
            data = self.get_request_data()
            r = self.save_one(self.db, data)
            if r.get('status') == 'success':
                op_type = 'update_volume' if r.get('update') else 'add_volume'
                self.add_op_log(op_type, context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except DbError as error:
            return self.send_db_error(error)


class VolumeDeleteApi(BaseHandler):
    URL = '/api/data/volume/delete'

    def post(self):
        """ 批量删除 """
        try:
            data = self.get_request_data()
            rules = [(v.not_both_empty, '_id', '_ids'), ]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            if data.get('_id'):
                _id = objectid.ObjectId(data.get('_id'))
                r = self.db.volume.delete_one({'_id': _id})
                self.add_op_log('delete_volume', target_id=str(_id), context=data.get('volume_code'))
            else:
                _ids = [objectid.ObjectId(i) for i in data.get('_ids')]
                r = self.db.volume.delete_many({'_id': {'$in': _ids}})
                self.add_op_log('delete_volume', target_id=str(data.get('_ids')))
            self.send_data_response(dict(deleted_count=r.deleted_count))

        except DbError as error:
            return self.send_db_error(error)
