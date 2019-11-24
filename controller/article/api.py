#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import hashlib
import os
import re
from PIL import Image
from controller.base import BaseHandler, DbError
from controller import errors
from controller.helper import get_date_time


class SaveArticleApi(BaseHandler):
    URL = '/api/article/save/@article_id'

    def post(self, article_id):
        """保存文章"""
        try:
            article = self.db.article.find_one({'article_id': article_id})
            if article:
                num = self.get_request_data().get('num') or 1
                cmp, hit_article_codes = find_one(article.get('ocr'), int(num))
                if cmp:
                    self.send_data_response(dict(cmp=cmp, hit_article_codes=hit_article_codes))
                else:
                    self.send_error_response(errors.no_object, message='未找到比对文本')
            else:
                self.send_error_response(errors.no_object, message='页面%s不存在' % article_name)

        except DbError as e:
            self.send_db_error(e)


class UploadImageHandler(BaseHandler):
    URL = '/php/imageUp.php'

    def post(self):
        """ 编辑器中的图片上传 """
        assert self.request.files and self.request.files['upfile']
        file = self.request.files['upfile'][0]
        if len(file['body']) > 1024 * 1024:
            return self.send_error(errors.upload_fail, reason='文件大小超出 1MB 限制')

        date = get_date_time()
        folder = date[:7].replace('-', 'p')

        m = hashlib.md5()
        m.update(file['body'])
        fid = m.hexdigest()[:16] + file['content_type'].replace('image/', '.')
        img_path = os.path.join(self.application.IMAGE_PATH, folder)
        filename = os.path.join(img_path, fid)
        if not re.search(r'\.(png|jpg|jpeg|gif|bmp)$', fid):
            return self.send_error_response(errors.upload_fail, message='不允许的文件类型')

        if not os.path.exists(img_path):
            os.makedirs(img_path)
        with open(filename, 'wb') as f:
            f.write(file['body'])
        filename, w, h = self.resize_image(filename)
        filename = filename.replace(self.application.IMAGE_PATH, '').strip('/\\')

        self.add_op_log('upload_image', context=file['filename'] + ':' + filename)
        self.send_data_response(dict(url=filename, w=w, h=h))

    @staticmethod
    def resize_image(filename, width=0, height=0):
        im = Image.open(filename)
        w, h = im.size
        width = width or 1024
        height = height or 768
        if w > width or h > height:
            if w > width:
                h = round(width * h / w)
                w = width
            if h > height:
                w = round(height * w / h)
                h = height
            im.thumbnail((int(w), int(h)), Image.ANTIALIAS)
            os.remove(filename)
            filename = re.sub(r'\.\w+$', '.png', filename)
            im.save(filename, 'png')
        return filename, int(w), int(h)
