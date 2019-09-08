#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR接口
@time: 2019/9/2
"""
from tornado import web
from tornado.escape import to_basestring
from urllib.parse import urlencode
from controller.base import BaseHandler
from controller import errors
from os import path
import logging
import re
import json


class RecognitionApi(BaseHandler):
    URL = '/api/data/ocr'

    @web.asynchronous
    def post(self):
        """藏经OCR接口"""
        def handle_response(r):
            img_file = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr', filename)
            with open(img_file, 'wb') as f:
                f.write(img[0]['body'])
            with open(img_file.split('.')[0] + '.json', 'w') as f:
                json.dump(r, f, ensure_ascii=False)

            self.render('data_ocr.html', page=r, img=self.static_url('upload/ocr/' + filename))

        data = self.get_request_data()
        if not data:
            data = dict(self.request.arguments)
            for k, v in data.items():
                data[k] = to_basestring(v[0])
        img = self.request.files.get('img')
        assert img
        filename = re.sub(r'[^A-Za-z0-9._-]', '', path.basename(img[0]['filename']))
        if len(filename.split('.')[0]) < 4:
            filename = '%d.%s' % (hash(img[0]['filename']) % 10000, filename.split('.')[-1])

        logging.info('recognize ' + filename)
        self.call_back_api('http://127.0.0.1:8010/ocr?%s' % urlencode(data), timeout=15,
                           handle_error=lambda t: self.send_error_response(errors.ocr, message=errors.ocr[1] % t),
                           body=img[0]['body'], method='POST', handle_response=handle_response)
