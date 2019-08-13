#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 如是藏经、大藏经
"""
import csv
from tornado.escape import to_basestring
from controller.base import BaseHandler
from meta.import_meta import import_tripitaka, import_volume, import_sutra, import_reel
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class UploadTripitakaApi(BaseHandler):
    URL = '/api/data/upload/tripitaka'

    def post(self):
        """ 批量上传藏数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            rows = list(csv.reader(fn))
            code, message = import_tripitaka(self.db, rows)
            if code == 200:
                self.send_data_response({'message': message})
            else:
                self.send_error_response((code, message))


class UploadVolumeApi(BaseHandler):
    URL = '/api/data/upload/volume'

    def post(self):
        """ 批量上传册数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            rows = list(csv.reader(fn))
            code, message = import_volume(self.db, rows)
            if code == 200:
                self.send_data_response({'message': message})
            else:
                self.send_error_response((code, message))


class UploadSutraApi(BaseHandler):
    URL = '/api/data/upload/sutra'

    def post(self):
        """ 批量上传经数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            rows = list(csv.reader(fn))
            code, message = import_sutra(self.db, rows)
            if code == 200:
                self.send_data_response({'message': message})
            else:
                self.send_error_response((code, message))


class UploadReelApi(BaseHandler):
    URL = '/api/data/upload/reel'

    def post(self):
        """ 批量上传卷数据 """
        upload_csv = self.request.files.get('csv')
        content = to_basestring(upload_csv[0]['body'])
        with StringIO(content) as fn:
            rows = list(csv.reader(fn))
            code, message = import_reel(self.db, rows)
            if code == 200:
                self.send_data_response({'message': message})
            else:
                self.send_error_response((code, message))