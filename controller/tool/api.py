#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/08/16
"""
import re
import json
import subprocess
from .esearch import find
from tornado.escape import to_basestring
from controller.text.variant import normalize
from controller.base import BaseHandler, DbError
from controller import errors as e
from urllib.parse import urlencode
from controller import helper
from os import path, remove
from PIL import Image
import logging



try:
    import punctuation

    punc_str = punctuation.punc_str
except Exception:
    punc_str = lambda s: s


class PunctuationApi(BaseHandler):
    URL = '/api/tool/punctuate'

    def post(self):
        """ 自动标点 """
        try:
            data = self.get_request_data()
            q = data.get('q', '').strip()
            res = punc_str(q) if q else ''
            self.send_data_response(dict(res=res))

        except DbError as e:
            self.send_db_error(e)


class CbetaSearchApi(BaseHandler):
    URL = '/api/tool/search'

    def post(self):
        """ CBETA检索 """

        def merge_kw(txt):
            # 将<kw>一</kw>，<kw>二</kw>格式替换为<kw>一，二</kw>
            regex = r'[，、：；。？！“”‘’「」『』（）%&*◎—……]+'
            txt = re.sub('</kw>(%s)<kw>' % regex, lambda r: r.group(1), txt)
            # 合并相邻的关键字
            txt = re.sub('</kw><kw>', '', txt)
            return txt

        data = self.get_request_data()
        q = data.get('q', '').strip()
        try:
            matches = find(q)
        except Exception as e:
            matches = [dict(hits=[str(e)])]

        for m in matches:
            try:
                highlights = {re.sub('</?kw>', '', v): merge_kw(v) for v in m['highlight']['normal']}
                hits = [highlights.get(normalize(r), r) for r in m['_source']['origin']]
                m['hits'] = hits
            except KeyError:
                m['hits'] = m.get('hits') or m['_source']['origin']

        self.send_data_response(dict(matches=matches))


class RecognitionApi(BaseHandler):
    URL = '/api/tool/ocr'

    def post(self):
        """对上传的一个藏经图作OCR的接口"""

        def handle_response(r):
            """OCR已完成的通知"""
            img_file = path.join(self.application.BASE_DIR, 'static', 'upload', 'ocr', filename)
            gif_file = img_file.split('.')[0] + '.gif'
            json_file = img_file.split('.')[0] + '.json'

            # 缓存图片和OCR结果到 upload/ocr 目录
            with open(img_file, 'wb') as f:
                f.write(img[0]['body'])
            with open(json_file, 'w') as f:
                r['create_time'] = helper.get_date_time()
                json.dump(r, f, ensure_ascii=False)

            # 缩小图片
            im = Image.open(img_file).convert('RGBA')
            w, h = im.size
            if w > 1200 or h > 1200:
                if w > 1200:
                    h = round(1200 * h / w)
                    w = 1200
                if h > 1200:
                    w = round(1200 * w / h)
                    h = 1200
                im.thumbnail((int(w), int(h)), Image.ANTIALIAS)

            # 图片加水印、变为灰度图，保存为gif
            try:
                mark = Image.open(path.join(path.dirname(__file__), 'rushi.png'))
                if mark.size != (w, h):
                    mark = mark.resize((w, h))
                im = Image.alpha_composite(im, mark)
            except ValueError as err:
                logging.error('%s: %s' % (img_file, str(err)))

            im.convert('L').save(gif_file, 'GIF')
            if gif_file != img_file:
                remove(img_file)

            subprocess.call(['gifsicle', '-o', gif_file, '-O3', '--careful', '--no-comments', '--no-names',
                             '--same-delay', '--same-loopcount', '--no-warnings', '--', gif_file])

            self.send_data_response(dict(name=path.basename(gif_file)))

        data = self.get_request_data()
        if not data:
            data = dict(self.request.arguments)
            for k, v in data.items():
                data[k] = to_basestring(v[0])
        img = self.request.files.get('img')
        assert img
        filename = re.sub(r'[^A-Za-z0-9._-]', '', path.basename(img[0]['filename']))  # 去掉路径、汉字和特殊符号
        ext = filename.split('.')[-1].lower()
        filename = '%s.%s' % (filename.split('.')[0], ext)
        if '_' not in filename:  # 如果图片文件名不是规范的页面名，则从路径提取藏别、卷册名，生成页面名
            m = re.search(r'([/\\][A-Za-z]{2})?([/\\][0-9]+){1,3}$', path.dirname(filename))
            if m:
                filename = re.sub(r'[/\\]', '_', m.group(0)[1:]) + '_' + filename
            if len(filename) < 7:
                filename = '%d.%s' % (hash(img[0]['filename']) % 10000, ext)
        data['filename'] = filename

        # 将图片内容转发到OCR服务，OCR结果将以JSON内容返回
        logging.info('recognize %s...' % filename)
        url = '%s?%s' % (self.config['ocr_api'], urlencode(data))
        self.call_back_api(
            url, connect_timeout=5, request_timeout=20, body=img[0]['body'], method='POST',
            handle_error=lambda t: self.send_error_response(e.ocr_err, message=e.ocr_err[1] % (t or '无法访问')),
            handle_response=handle_response
        )
