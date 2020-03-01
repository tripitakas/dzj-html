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

    def get_hash_name(self, img_name, cid='', use_salt=True):
        img_name += '_' + cid if cid else ''
        salt = self.get_cfg('web_img.salt')
        if use_salt and salt:
            md5 = hashlib.md5()
            md5.update((img_name + salt).encode('utf-8'))
            return '%s_%s.jpg' % (img_name, md5.hexdigest())
        else:
            return img_name + '.jpg'

    @staticmethod
    def resize_binary(img, width=1024, height=1024, center=False):
        w, h = img.size
        if w > width or h > height:
            if w > width:
                w, h = width, int(width * h / w)
            if h > height:
                w, h = int(height * w / h), height
            img = img.resize((w, h), Image.BICUBIC)

        # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 19, 10)
        if center:
            new_im = Image.new('L', (width, height), 'white')
            new_im.paste(img, ((width - w) // 2, (height - h) // 2))
        return img

    def get_big_img(self, page_name):
        """ 读大图。自动检测page_name中的hash值"""
        has_hash = len(page_name.split('_')[-1]) > 30
        page_name = self.get_hash_name(page_name.split('_')[0] if has_hash else page_name, use_salt=False)
        inner_path = '/'.join(page_name.split('_')[:-2 if has_hash else -1])
        img_path = 'pages/{0}/{1}'.format(inner_path, page_name)
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
            self.oss_big = Oss(my_cloud, key_id, key_secret)
        if self.oss_big and self.oss_big.readable:
            tmp_file = path.join(BASE_DIR, 'temp', 'cut', img_path)
            if not path.exists(path.dirname(tmp_file)):
                os.makedirs(path.dirname(tmp_file))
            self.oss_big.download_file(img_path, tmp_file)
            return tmp_file
        raise OSError('oss not exist or not readable')

    def write_web_img(self, img_obj, img_name, img_type='char'):
        """ 写web图。img_obj为Image对象，img_name不带hash值"""
        inner_path = '/'.join(img_name.split('_')[:-1])
        img_path = '{0}s/{1}/{2}.jpg'.format(img_type, inner_path, self.get_hash_name(img_name))
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
            self.oss_web = Oss(my_cloud, key_id, key_secret, access='write')
        if self.oss_web and self.oss_web.writeable:
            tmp_file = path.join(BASE_DIR, 'temp', 'cut', img_path)
            if not path.exists(path.dirname(tmp_file)):
                os.makedirs(path.dirname(tmp_file))
            img_obj.save(tmp_file)
            self.oss_web.upload_file(img_path, tmp_file)
            return tmp_file
        raise OSError('oss not exist or not writeable')

    def cut_img(self, chars):
        """ 切图，包括字图和列图"""
        # 去掉无效页面
        log = dict(success=[], fail=[], exist=[], columns=[])
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
            img_file = None
            try:
                img_file = self.get_big_img(page_name)
            except Exception:
                log['fail'].extend([dict(id=c['id'], reason='page img not exist') for c in chars_todo])

            try:
                img_page = Image.open(img_file).convert('L')
            except AttributeError:
                img_page = None
            if img_page is None:
                log['fail'].extend([dict(id=c['id'], reason='fail to open page') for c in chars_todo])
                continue
            iw, ih = img_page.size
            if iw != page['width'] or ih != page['height']:
                img_page = img_page.resize((page['width'], page['height']), Image.BICUBIC)
            # 字框切图
            for c in chars_todo:
                oc = [ch for ch in page['chars'] if ch['cid'] == c['cid']]
                if not oc:
                    log['fail'].append(dict(id=c['id'], reason='origin cid not exist'))
                    continue
                if c['has_img'] and not self.kwargs.get('reset') and cmp_obj(c, oc[0], ['x', 'y', 'w', 'h']):
                    log['exist'].append(c)
                    continue
                x, y, h, w = int(c['pos']['x']), int(c['pos']['y']), int(c['pos']['h']), int(c['pos']['w'])
                try:
                    img_c = img_page.crop((x, y, min(iw, x + w), min(ih, y + h)))
                    img_c = self.resize_binary(img_c, 64, 64, True)
                    img_name = '%s_%s' % (c['page_name'], c['cid'])
                    self.write_web_img(img_c, img_name, 'char')
                    chars_done.append(c)
                except Exception:
                    log['fail'].append(dict(id=c['id'], reason='write error'))

            # 列框切图
            columns_todo, columns_done = list(set(c['column_cid'] for c in chars_done)), []
            for cid in columns_todo:
                column = [c for c in page['columns'] if c['cid'] == cid]
                if not column:
                    continue
                c = column[0]
                x, y, h, w = int(c['x']), int(c['y']), int(c['h']), int(c['w'])
                try:
                    img_c = img_page.crop((x, y, min(iw, x + w), min(ih, y + h)))
                    img_c = self.resize_binary(img_c, 64, 64, True)
                    img_name = '%s_%s' % (c['page_name'], c['cid'])
                    self.write_web_img(img_c, img_name, 'column')
                    columns_done.append(c)
                except Exception:
                    pass

            log['success'].extend(chars_done)
            log['columns'].extend(columns_done)

        return log


class Oss(object):

    def __init__(self, bucket_host, key_id, key_secret, internal=True, access='read', **kwargs):
        """ OSS读写默认以内网方式进行"""
        if internal and '-internal' not in bucket_host:  # 获取内网访问地址
            bucket_host = bucket_host.replace('.aliyuncs.com', '-internal.aliyuncs.com')
        auth = oss2.Auth(key_id, key_secret)
        bucket_name = re.sub(r'http[s]?://', '', bucket_host).split('.')[0]
        oss_host = bucket_host.replace(bucket_name + '.', '')

        self.bucket_host = bucket_host
        self.bucket = oss2.Bucket(auth, oss_host, bucket_name)
        self.readable = self.is_readable() if access == 'read' else None
        self.writeable = self.is_writeable() if access == 'write' else None

    def is_readable(self):
        try:
            self.bucket.list_objects('')
            return True
        except oss2.exceptions:
            return False

    def is_writeable(self):
        try:
            self.bucket.put_object('1.tmp', '')
            self.bucket.delete_object('1.tmp')
            return True
        except oss2.exceptions:
            return False

    def download_file(self, oss_file, save_path=None):
        self.bucket.get_object_to_file(oss_file, save_path)

    def upload_file(self, oss_file, local_file):
        self.bucket.put_object_from_file(oss_file, local_file)
