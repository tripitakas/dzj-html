#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
from bson import objectid
import controller.errors as e
import controller.validate as v
from tornado.escape import to_basestring
from controller.base import BaseHandler, DbError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Tripitaka(object):
    fields = ['tripitaka_code', 'name', 'short_name', 'store_pattern', 'img_available', 'img_prefix', 'img_suffix']

    @classmethod
    def get_item(cls, item):
        for k in list(item.keys()):
            if k not in cls.fields + ['_id']:
                del item[k]
        if item.get('_id') and isinstance(item.get('_id'), str):
            item['_id'] = objectid.ObjectId(item.get('_id'))
        else:
            del item['_id']

        return item

    @classmethod
    def validate(cls, item):
        assert isinstance(item, dict)
        rules = [
            (v.not_empty, 'tripitaka_code', 'name', 'short_name'),
            (v.is_tripitaka, 'tripitaka_code'),
        ]
        err = v.validate(item, rules)
        return err

    @classmethod
    def save_one(cls, db, item):
        item = cls.get_item(item)
        err = cls.validate(item)
        if err:
            return dict(status='failed', errors=err)

        data = db.tripitaka.find_one({'tripitaka_code': item.get('tripitaka_code')})
        if item.get('_id'):  # 更新
            if data and data.get('_id') != item.get('_id'):
                return dict(status='failed', errors=e.tripitaka_code_existed)
            else:
                db.tripitaka.update_one({'_id': item.get('_id')}, {'$set': item})
                return dict(status='success', id=item.get('_id'), update=True)
        else:  # 新增
            if data:
                return dict(status='failed', errors=e.tripitaka_code_existed)
            else:
                db.tripitaka.insert_one(item)
                return dict(status='success', id=item.get('_id'), update=False)

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
            heads = rows[0]
            need_fields = [r for r in cls.fields if r not in heads]
            if need_fields:
                return dict(status='failed', code=e.tripitaka_field_error[0],
                            message='缺以下字段：%s' % ','.join(need_fields))
            items = [{heads[i]: item for i, item in enumerate(row)} for row in rows[1:]]

        valid_items, valid_codes, error_codes = [], [], []
        for i, item in enumerate(items):
            err = cls.validate(item)
            if err:
                error_codes.append([item.get('tripitaka_code'), err])
            elif item.get('tripitaka_code') in valid_codes:
                error_codes.append([item.get('tripitaka_code'), e.tripitaka_code_duplicated])
            else:
                valid_items.append(cls.get_item(item))
                valid_codes.append(item.get('tripitaka_code'))

        existed_code = []
        if check_existed:
            existed_record = list(db.tripitaka.find({'tripitaka_code': {'$in': valid_codes}}))
            existed_code = [i.get('tripitaka_code') for i in existed_record]
            existed_items = [i for i in valid_items if i.get('tripitaka_code') in existed_code]
            valid_items = [i for i in valid_items if i.get('tripitaka_code') not in existed_code]
            for item in existed_items:
                db.tripitaka.update_one({'tripitaka_code': item.get('tripitaka_code')}, {'$set': item})

        if valid_items:
            db.tripitaka.insert_many(valid_items)

        error_tip = ('：' + ','.join([i[0] for i in error_codes])) if error_codes else ''
        message = '总共%s条记录，插入%s条，更新%s条，%s条无效数据%s。' % (
            len(items), len(valid_items), len(existed_code), len(error_codes), error_tip)
        return dict(status='success', errors=error_codes, message=message)


class TripitakaUploadApi(BaseHandler, Tripitaka):
    URL = '/api/data/tripitaka/upload'

    def post(self):
        """ 批量上传藏数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            r = self.save_many(self.db, file_stream=fn)
            if r.get('status') == 'success':
                self.add_op_log('upload_tripitaka', context=r.get('message'))
                self.send_data_response({'message': r.get('message'), 'errors': r.get('errors')})
            else:
                self.send_error_response((r.get('code'), r.get('message')))


class TripitakaAddOrUpdateApi(BaseHandler, Tripitaka):
    URL = '/api/data/tripitaka'

    def post(self):
        """ 新增或修改 """
        try:
            data = self.get_request_data()
            r = self.save_one(self.db, data)
            if r.get('status') == 'success':
                self.add_op_log('add_or_update_tripitaka', context=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except DbError as error:
            return self.send_db_error(error)


class TripitakaDeleteApi(BaseHandler):
    URL = '/api/data/tripitaka/delete'

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
                r = self.db.tripitaka.delete_one({'_id': _id})
                self.add_op_log('delete_tripitaka', target_id=str(_id), context=r.get('name'))
            else:
                _ids = [objectid.ObjectId(i) for i in data.get('_ids')]
                r = self.db.tripitaka.delete_many({'_id': {'$in': _ids}})
                self.add_op_log('delete_tripitaka', target_id=str(data.get('_ids')))
            self.send_data_response(dict(deleted_count=r.deleted_count))

        except DbError as error:
            return self.send_db_error(error)
