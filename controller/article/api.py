#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/11/17
"""
import hashlib
import os
import re
from PIL import Image
from datetime import datetime
from bson.objectid import ObjectId
from controller.base import BaseHandler, DbError
from controller import errors
from controller.helper import get_date_time
import controller.validate as v


class DeleteArticleApi(BaseHandler):
    URL = ['/api/article/delete/@article_id',
           '/api/article/del_my/@article_id']

    def get(self, article_id):
        """删除文章"""
        try:
            cond = {'article_id': article_id} if '-' in article_id else {'_id': ObjectId(article_id)}
            article = self.db.article.find_one(cond)

            if not article:
                return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id)
            self.db.article.update_one({'_id': article['_id']}, {'$set': dict(deleted=True)})
            self.add_op_log('delete_article', target_id=article['_id'], context=article['title'])
            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class SaveArticleApi(BaseHandler):
    URL = '/api/article/save/@article_id'

    def post(self, article_id):
        """保存文章"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'title', 'category', 'content')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)

            info = dict(title=data['title'].strip(), category=data['category'].strip(),
                        content=data['content'].strip(),
                        images=re.findall(r'<img src="http[^"]+?upload/([^"]+)".+?>', data['content']))

            article = len(article_id) > 3
            if article:
                cond = {'article_id': article_id} if '-' in article_id else {'_id': ObjectId(article_id)}
                article = self.db.article.find_one(cond)
                if article is None and '_id' in cond:
                    return self.send_error_response(errors.no_object, message='文章%s不存在' % article_id)

            if data.get('article_id'):
                if article and article.get('article_id') != data['article_id']:
                    if not re.match(r'^[a-z]+-[-\w]+$', data['article_id']):
                        return self.send_error_response(errors.invalid_digit, message='文章标识格式错误')
                    if self.db.article.find_one({'article_id': data['article_id']}):
                        return self.send_error_response(errors.record_existed, message='文章标识已被占用')
                info['article_id'] = data['article_id']

            if article:
                r = self.db.article.update_one({'_id': article['_id']}, {'$set': info})
                info['id'] = str(article['_id'])
                info['modified'] = r.modified_count
                if r.modified_count:
                    self.db.article.update_one({'_id': article['_id']}, {'$set': dict(
                        updated_time=datetime.now(), updated_by=self.current_user['name'])})
                    self.add_op_log('save_article', target_id=article['_id'], context=info['title'])
            else:
                info.update(dict(create_time=datetime.now(),
                                 author_id=self.current_user['_id'],
                                 author_name=self.current_user['name']))
                if '-' in article_id:
                    info['article_id'] = article_id
                r = self.db.article.insert_one(info)
                info['id'] = str(r.inserted_id)
                self.add_op_log('add_article', target_id=r.inserted_id, context=info['title'])

            info.pop('content')
            self.send_data_response(info)

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
