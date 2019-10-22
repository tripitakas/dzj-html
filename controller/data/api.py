#!/usr/bin/env python
# -*- coding: utf-8 -*-


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


class DataPublishOcrApi(BaseHandler):
    URL = '/api/data/publish_ocr'

    def post(self):
        pass


class DataUploadCloudApi(BaseHandler):
    URL = '/api/data/upload_cloud'

    def post(self):
        pass
