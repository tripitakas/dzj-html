#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import os
import re
import hashlib
from PIL import Image
from datetime import datetime
from bson.objectid import ObjectId
from controller import errors
import controller.validate as v
from controller.helper import get_date_time
from controller.base import BaseHandler, DbError


class ArticleDeleteApi(BaseHandler):
    URL = '/api/article/delete'

    def post(self):
        """ 删除文章"""
        try:
            rules = [(v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            if self.data.get('_id'):
                r = self.db.article.delete_one({'_id': ObjectId(self.data['_id'])})
                self.add_op_log('delete_article', target_id=self.data['_id'])
            else:
                r = self.db.article.delete_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}})
                self.add_op_log('delete_article', target_id=self.data['_ids'])
            self.send_data_response(dict(count=r.deleted_count))

        except DbError as error:
            return self.send_db_error(error)


class ArticleAddOrUpdateApi(BaseHandler):
    URL = '/api/article/(add|update)'

    def post(self, mode):
        """ 保存文章"""
        try:
            fields = ['title', 'article_id', 'category', 'active', 'content'] + ['_id'] if mode == 'update' else []
            rules = [(v.not_empty, *fields), (v.is_article, 'article_id')]
            self.validate(self.data, rules)

            article_id = self.data['article_id'].strip()
            images = re.findall(r'<img src="http[^"]+?upload/([^"]+)".+?>', self.data['content'])
            info = dict(title=self.data['title'].strip(), article_id=article_id, category=self.data['category'].strip(),
                        active=self.data['active'].strip(), content=self.data['content'].strip(), images=images,
                        updated_time=self.now(), updated_by=self.username)

            if mode == 'update':
                _id = ObjectId(self.data['_id'])
                article = self.db.article.find_one({'article_id': article_id, '_id': {'$ne': _id}})
                if article:
                    return self.send_error_response(errors.doc_existed, message='文章标识已被占用')
                r = self.db.article.update_one({'_id': _id}, {'$set': info})
                if not r.matched_count:
                    return self.send_error_response(errors.no_object, message='文章不存在')
                self.add_op_log('update_article', target_id=_id, context=info['title'])
            else:
                info.update(dict(create_time=self.now(), author_id=self.user_id, author_name=self.username))
                r = self.db.article.insert_one(info)
                self.add_op_log('add_article', target_id=r.inserted_id, context=info['title'])
                info['_id'] = str(r.inserted_id)

            info.pop('content', 0)
            self.send_data_response(info)

        except DbError as error:
            return self.send_db_error(error)


class UploadImageApi(BaseHandler):
    URL = '/php/imageUp.php'

    def post(self):
        """ 编辑器中的图片上传
        url参数和返回值要适配editor
        """
        assert self.request.files and self.request.files['upfile']
        file = self.request.files['upfile'][0]
        if len(file['body']) > 1024 * 1024:
            return self.send_error(errors.upload_fail, reason='文件不允许超过1MB')

        date = get_date_time()
        folder = date[:7].replace('-', 'p')

        m = hashlib.md5()
        m.update(file['body'])
        fid = m.hexdigest()[:16] + file['content_type'].replace('image/', '.')
        upload_path = os.path.join(self.application.BASE_DIR, 'static', 'upload')
        img_path = os.path.join(upload_path, folder)
        filename = os.path.join(img_path, fid)
        if not re.search(r'\.(png|jpg|jpeg|gif|bmp)$', fid):
            return self.send_error_response(errors.upload_fail, message='不允许的文件类型')

        if not os.path.exists(img_path):
            os.makedirs(img_path)
        with open(filename, 'wb') as f:
            f.write(file['body'])
        filename, w, h = self.resize_image(filename)
        filename = filename.replace(upload_path, '').strip('/\\')

        self.add_op_log('upload_image', context='%s,%dx%d' % (filename, w, h))
        self.write(dict(state='SUCCESS', url=filename, w=w, h=h))

    @staticmethod
    def resize_image(filename, width=0, height=0):
        im = Image.open(filename)
        w, h = im.size
        width = width or 2048
        height = height or 1500
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
