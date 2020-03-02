#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import oss2
import hashlib
from os import path
from PIL import Image
from controller.helper import BASE_DIR, prop, cmp_obj


class Cut(object):

    def __init__(self, db, cfg, **kwargs):
        self.db = db
        self.cfg = cfg
        self.oss_big = self.oss_web = None
        self.kwargs = kwargs

    def get_cfg(self, key):
        return prop(self.cfg, key)

    @staticmethod
    def get_hash_name(img_name, cid='', salt=''):
        img_name += '_' + cid if cid else ''
        if salt:
            md5 = hashlib.md5()
            md5.update((img_name + salt).encode('utf-8'))
            return '%s_%s' % (img_name, md5.hexdigest())
        else:
            return img_name

    @staticmethod
    def resize_binary(img, width=1024, height=1024, center=False):
        w, h = img.size
        if w > width or h > height:
            if w > width:
                w, h = width, int(width * h / w)
            if h > height:
                w, h = int(height * w / h), height
            img = img.resize((w, h), Image.BICUBIC)

        if center:
            new_im = Image.new('L', (width, height), 'white')
            new_im.paste(img, ((width - w) // 2, (height - h) // 2))
        return img

    def cut_img(self, chars):
        """ 切图，包括字图和列图"""
        # 去掉无效页面
        log = dict(success=[], fail=[], exist=[], column_success=[], column_fail=[])
        page_names = list(set(c['page_name'] for c in chars))
        fields = ['name', 'width', 'height', 'columns', 'chars']
        pages = list(self.db.page.find({'name': {'$in': page_names}}, {f: 1 for f in fields}))
        valid_names = [p['name'] for p in pages]
        log['fail'].extend([
            dict(id=c['id'], reason='page not in db') for c in chars if c['page_name'] not in valid_names
        ])
        page_dict = {p['name']: p for p in pages}
        # 处理有效页面
        for page_name in valid_names:
            page = page_dict.get(page_name)
            chars_todo, chars_done = [c for c in chars if c['page_name'] == page_name], []
            # 获取大图
            img_page = None
            try:
                img_file = self.get_big_img(page_name)
                img_page = Image.open(img_file).convert('L')
            except Exception as e:
                reason = '[%s] %s' % (e.__class__.__name__, str(e))
                log['fail'].extend([dict(id=c['id'], reason=reason) for c in chars_todo])
            ih, iw = img_page.size
            ph, pw = int(page['width']), int(page['height'])
            if iw != pw or ih != ph:
                img_page = img_page.resize((pw, ph), Image.BICUBIC)
            # 字框切图
            for c in chars_todo:
                oc = [ch for ch in page['chars'] if ch['cid'] == c['cid']]
                if not oc:
                    log['fail'].append(dict(id=c['id'], reason='origin cid not exist'))
                    continue
                if c.get('has_img') and not self.kwargs.get('reset') and cmp_obj(c, oc[0], ['x', 'y', 'w', 'h']):
                    if c.get('has_img') and cmp_obj(c, oc[0], ['x', 'y', 'w', 'h']):
                        log['exist'].append(c['id'])
                        continue
                x, y, h, w = int(c['pos']['x']), int(c['pos']['y']), int(c['pos']['h']), int(c['pos']['w'])
                # img_c = img_page.crop((x, y, min(pw, x + w), min(ph, y + h)))
                img_c = img_page.crop((x, y, x + w, y + h))
                if img_c is not None:
                    try:
                        img_c = self.resize_binary(img_c, 64, 64, True)
                        img_name = '%s_%s' % (page_name, c['cid'])
                        self.write_web_img(img_c, img_name, 'char')
                        chars_done.append(c)
                    except Exception as e:
                        log['fail'].append(dict(id=c['id'], reason='[%s] %s' % (e.__class__.__name__, str(e))))
            # 列框切图
            columns_todo, columns_done = list(set(c['column_cid'] for c in chars_done)), []
            for cid in columns_todo:
                column = [c for c in page['columns'] if c['cid'] == cid]
                if not column:
                    continue
                c = column[0]
                x, y, h, w = int(c['x']), int(c['y']), int(c['h']), int(c['w'])
                img_c = img_page.crop((x, y, x + w, y + h))
                if img_c is not None:
                    try:
                        img_c = self.resize_binary(img_c, 64, 64, True)
                        img_name = '%s_%s' % (page_name, c['cid'])
                        self.write_web_img(img_c, img_name, 'column')
                        columns_done.append('%s_%s' % (page_name, c['cid']))
                    except Exception as e:
                        reason = '[%s] %s' % (e.__class__.__name__, str(e))
                        log['column_fail'].append(dict(id='%s_%s' % (page_name, c['cid']), reason=reason))
            log['success'].extend([c['id'] for c in chars_done])
            log['column_success'].extend(columns_done)

        return log

    def get_big_img(self, page_name):
        """ 读大图。page_name中不带hash值"""
        inner_path = '/'.join(page_name.split('_')[:-1])
        if self.get_cfg('big_img.with_hash'):
            page_name = self.get_hash_name(page_name, salt=self.get_cfg('big_img.salt'))
        img_path = 'pages/{0}/{1}.jpg'.format(inner_path, page_name)
        local_path = self.get_cfg('big_img.local_path')
        if local_path:
            if local_path[0] != '/':
                local_path = path.join(BASE_DIR, local_path)
            img_file = path.join(local_path, img_path)
            if not path.exists(img_file):
                raise OSError('%s not exist' % img_file)
            return img_file
        my_cloud = self.get_cfg('big_img.my_cloud')
        if not self.oss_big and my_cloud:
            key_id, key_secret = self.get_cfg('big_img.key_id'), self.get_cfg('big_img.key_secret')
            self.oss_big = Oss(my_cloud, key_id, key_secret, self.get_cfg('big_img.use_internal'))
        if self.oss_big and self.oss_big.is_readable():
            tmp_file = path.join(BASE_DIR, 'temp', 'cut', img_path)
            if not path.exists(path.dirname(tmp_file)):
                os.makedirs(path.dirname(tmp_file))
            self.oss_big.download_file(img_path, tmp_file)
            return tmp_file
        raise OSError('oss not exist or not readable')

    def write_web_img(self, img_obj, img_name, img_type='char'):
        """ 写web图。img_obj为Image对象，img_name不带hash值"""
        salt = self.get_cfg('web_img.salt')
        inner_path = '/'.join(img_name.split('_')[:-1])
        img_path = '{0}s/{1}/{2}.jpg'.format(img_type, inner_path, self.get_hash_name(img_name, salt=salt))
        local_path = self.get_cfg('web_img.local_path')
        if local_path:
            if local_path[0] != '/':
                local_path = path.join(BASE_DIR, local_path)
            img_path = path.join(local_path, img_path)
            if not path.exists(path.dirname(img_path)):
                os.makedirs(path.dirname(img_path))
            img_obj.save(img_path)
            return img_path
        my_cloud = self.get_cfg('web_img.my_cloud')
        if not self.oss_web and my_cloud:
            key_id, key_secret = self.get_cfg('web_img.key_id'), self.get_cfg('web_img.key_secret')
            self.oss_web = Oss(my_cloud, key_id, key_secret, self.get_cfg('web_img.use_internal'))
        if self.oss_web and self.oss_web.is_writeable():
            tmp_file = path.join(BASE_DIR, 'temp', 'cut', img_path)
            if not path.exists(path.dirname(tmp_file)):
                os.makedirs(path.dirname(tmp_file))
            img_obj.save(tmp_file)
            self.oss_web.upload_file(img_path, tmp_file)
            return tmp_file
        raise OSError('oss not exist or not writeable')


class Oss(object):

    def __init__(self, bucket_host, key_id, key_secret, use_internal=True, **kwargs):
        """ OSS读写默认以内网方式进行"""
        if use_internal and '-internal' not in bucket_host:
            bucket_host = bucket_host.replace('.aliyuncs.com', '-internal.aliyuncs.com')
        if not use_internal:
            bucket_host = bucket_host.replace('-internal.aliyuncs.com', '.aliyuncs.com')

        auth = oss2.Auth(key_id, key_secret)
        bucket_name = re.sub(r'http[s]?://', '', bucket_host).split('.')[0]
        oss_host = bucket_host.replace(bucket_name + '.', '')
        self.bucket_host = bucket_host
        self.bucket = oss2.Bucket(auth, oss_host, bucket_name)
        self.readable = self.writeable = None

    def is_readable(self):
        if self.readable is None:
            try:
                self.bucket.list_objects('')
                self.readable = True
            except oss2.exceptions:
                self.readable = False
        return self.readable

    def is_writeable(self):
        if self.writeable is None:
            try:
                self.bucket.put_object('1.tmp', '')
                self.bucket.delete_object('1.tmp')
                self.writeable = True
            except oss2.exceptions:
                self.writeable = False
        return self.writeable

    def download_file(self, oss_file, local_file):
        self.bucket.get_object_to_file(oss_file, local_file)

    def upload_file(self, oss_file, local_file):
        self.bucket.put_object_from_file(oss_file, local_file)
