#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 藏经OCR接口
@time: 2019/9/2
"""
from tornado.escape import to_basestring
from urllib.parse import urlencode
from controller.base import BaseHandler
from controller import errors
from controller.layout.v2 import calc
from os import path
import logging
import re
import json


class RecognitionApi(BaseHandler):
    URL = '/api/data/ocr'

    def post(self):
        """藏经OCR接口"""
        def handle_response(r):
            img_file = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr', filename)
            with open(img_file, 'wb') as f:
                f.write(img[0]['body'])
            with open(img_file.split('.')[0] + '.json', 'w') as f:
                json.dump(r, f, ensure_ascii=False)

            self.render('data_ocr.html', page=self.ocr2page(r), img=self.static_url('upload/ocr/' + filename))

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
        data['filename'] = filename
        self.call_back_api('http://127.0.0.1:8010/ocr?%s' % urlencode(data), connect_timeout=10,
                           handle_error=lambda t: self.send_error_response(errors.ocr, message=errors.ocr[1] % t),
                           body=img[0]['body'], method='POST', handle_response=handle_response)

    @staticmethod
    def ocr2page(page):
        def union(r1, r2):
            if not r1:
                r1 = list(r2)
            else:
                r1[0] = min(r1[0], r2[0])  # x1
                r1[1] = min(r1[1], r2[1])  # y1
                r1[2] = max(r1[2], r2[2])  # x2
                r1[3] = max(r1[3], r2[3])  # y2
            return r1

        def union_list(items):
            ret = None
            for r in items:
                ret = union(ret, r)
            return dict(x=ret[0], y=ret[1], w=ret[2] - ret[0], h=ret[3] - ret[1])

        page['blocks'] = [union_list(page['chars_pos'])]
        page['columns'] = []
        page['chars'] = [dict(x=c[0], y=c[1], w=c[2] - c[0], h=c[3] - c[1],
                              cc=page['chars_cc'][i], txt=page['chars_text'][i])
                         for i, c in enumerate(page['chars_pos'])]
        chars = calc(page['chars'], page['blocks'], page['columns'])
        for c_i, c in enumerate(chars):
            page['chars'][c_i]['char_id'] = 'b%dc%dc%d' % (c['block_id'], c['column_id'], c['column_order'])
            page['chars'][c_i]['block_no'] = c['block_id']
            page['chars'][c_i]['line_no'] = c['column_id']
            page['chars'][c_i]['char_no'] = chars[c_i]['no'] = c['column_order']
        return page
