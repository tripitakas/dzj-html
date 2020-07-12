#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 从char表提取字图。
# 提取字图时，原图相关参数在app.yml中的big_img中指定，包括：
# 1. local_path 本地路径。如果有值，则从本地路径中获取原图
# 2. my_cloud 云端路径。如果本地路径为空，则从云端路径获取原图
# 2.1 use_internal 是否使用阿里云的内网模式访问
# 2.2 key_id 云端访问key_id
# 2.3 key_secret: 云端访问秘钥
# 3. with_hash 原图是否带hash后缀
# 4. salt hash盐值
# python3 utils/extract_img.py --condition= --user_name=


import os
import sys
import json
import hashlib
import pymongo
from os import path
from PIL import Image

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from utils.oss import Oss
from controller import helper as hp
from controller.base import BaseHandler as Bh


class Cut(object):

    def __init__(self, db, cfg, **kwargs):
        self.db = db
        self.cfg = cfg
        self.oss_big = self.oss_web = None
        self.kwargs = kwargs

    def get_cfg(self, key):
        return hp.prop(self.cfg, key)

    @staticmethod
    def get_hash_name(img_name, cid='', salt=''):
        img_name += '_' + cid if cid else ''
        if salt and len(img_name.split('_')[-1]) < 20:
            md5 = hashlib.md5()
            md5.update((img_name + salt).encode('utf-8'))
            return '%s_%s' % (img_name, md5.hexdigest())
        else:
            return img_name

    @staticmethod
    def resize_binary(img, width=1024, height=1024):
        w, h = img.size
        if w > width or h > height:
            if w > width:
                w, h = width, int(width * h / w)
            if h > height:
                w, h = int(height * w / h), height
            img = img.resize((w, h), Image.BICUBIC)
        return img

    def cut_img(self, chars):
        """ 切图，包括字图和列图"""
        # 去掉无效页面
        log = dict(cut_char_success=[], cut_char_failed=[], cut_char_existed=[],
                   cut_column_failed=[], cut_column_success=[])
        page_names = list(set(c['page_name'] for c in chars))
        fields = ['name', 'width', 'height', 'columns', 'chars']
        pages = list(self.db.page.find({'name': {'$in': page_names}}, {f: 1 for f in fields}))
        valid_names = [p['name'] for p in pages]
        log['cut_char_failed'].extend([
            dict(id=c['name'], reason='page not in db') for c in chars if c['page_name'] not in valid_names
        ])
        page_dict = {p['name']: p for p in pages}
        # 处理有效页面
        for i, page_name in enumerate(valid_names):
            page = page_dict.get(page_name)
            chars_todo, chars_done = [c for c in chars if c['page_name'] == page_name], []
            # 获取大图
            try:
                img_file = self.get_big_img(page_name)
                img_page = Image.open(img_file).convert('L')
            except Exception as e:
                reason = '[%s] %s' % (e.__class__.__name__, str(e))
                log['cut_char_failed'].extend([dict(id=c['name'], reason=reason) for c in chars_todo])
                print(reason)
                continue
            iw, ih = img_page.size
            pw, ph = int(page['width']), int(page['height'])
            if iw != pw or ih != ph:
                img_page = img_page.resize((pw, ph), Image.BICUBIC)
                iw, ih = img_page.size
            # 字框切图
            for c in chars_todo:
                oc = [ch for ch in page['chars'] if ch['cid'] == c['cid']]
                if not oc:
                    log['cut_char_failed'].append(dict(id=c['name'], reason='origin cid not exist'))
                    continue
                if c.get('has_img') and not self.kwargs.get('regen') and hp.cmp_obj(c, oc[0], ['x', 'y', 'w', 'h']):
                    if c.get('has_img') and hp.cmp_obj(c, oc[0], ['x', 'y', 'w', 'h']):
                        log['cut_char_existed'].append(c['name'])
                        continue
                x, y, h, w = int(c['pos']['x']), int(c['pos']['y']), int(c['pos']['h']), int(c['pos']['w'])
                try:
                    img_c = img_page.crop((x, y, min(iw, x + w), min(ih, y + h)))
                    img_c = self.resize_binary(img_c, 64, 64)
                    img_name = '%s_%s' % (page_name, c['cid'])
                    self.write_web_img(img_c, img_name, 'char')
                    chars_done.append(c)
                except Exception as e:
                    log['cut_char_failed'].append(dict(id=c['name'], reason='[%s] %s' % (e.__class__.__name__, str(e))))
                    print(e)

            # 列框切图
            columns_todo, columns_done = list(set((c['column'] or {}).get('cid', 0) for c in chars_done)), []
            print('%d %s: %d char images generated from %d chars, %d columns' % (
                i + 1, page_name, len(chars_done), len(chars_todo), len(columns_todo)))

            for cid in columns_todo:
                column = [c for c in page['columns'] if c['cid'] == cid]
                if not column:
                    continue
                c = column[0]
                img_name = '%s_%s' % (page_name, c['cid'])
                x, y, h, w = int(c['x']) - 1, int(c['y']) - 1, int(c['h']) + 1, int(c['w']) + 1
                try:
                    img_c = img_page.crop((x, y, min(iw, x + w), min(ih, y + h)))
                    if iw < x + w or ih < y + h:
                        new_im = Image.new('L', (w, h), 'white')
                        new_im.paste(img_c)
                        img_c = new_im
                    img_c = self.resize_binary(img_c, 200, 1024)
                    self.write_web_img(img_c, img_name, 'column')
                    columns_done.append(img_name)
                except Exception as e:
                    reason = '[%s] %s' % (e.__class__.__name__, str(e))
                    log['cut_column_failed'].append(dict(id=img_name, reason=reason))
            log['cut_char_success'].extend([c['name'] for c in chars_done])
            log['cut_column_success'].extend(columns_done)

        return log

    def get_big_img(self, page_name, inner_path=None):
        """ 读大图。page_name中不带hash值"""
        inner_path = inner_path or '/'.join(page_name.split('_')[:-1])
        if self.get_cfg('big_img.with_hash'):
            page_name = self.get_hash_name(page_name, salt=self.get_cfg('big_img.salt'))
        img_path = 'pages/{0}/{1}.jpg'.format(inner_path, page_name)
        local_path = self.get_cfg('big_img.local_path')
        if local_path:
            if local_path[0] != '/':
                local_path = path.join(hp.BASE_DIR, local_path)
            img_file = path.join(local_path, img_path)
            if not path.exists(img_file):
                if path.exists(img_file.replace('pages/', '')):
                    img_file = img_file.replace('pages/', '')
                elif path.exists(path.join(local_path, page_name + '.jpg')):
                    img_file = path.join(local_path, page_name + '.jpg')
                else:
                    alt_file = len(inner_path) > 2 and self.get_big_img(page_name, page_name[:2])
                    if alt_file:
                        img_file = alt_file
                    else:
                        raise OSError('%s not exist' % img_file)
            return img_file
        my_cloud = self.get_cfg('big_img.my_cloud')
        if not self.oss_big and my_cloud:
            key_id, key_secret = self.get_cfg('big_img.key_id'), self.get_cfg('big_img.key_secret')
            self.oss_big = Oss(my_cloud, key_id, key_secret, self.get_cfg('big_img.use_internal'))
        if self.oss_big and self.oss_big.is_readable():
            tmp_file = path.join(hp.BASE_DIR, 'temp', 'cut', img_path)
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
                local_path = path.join(hp.BASE_DIR, local_path)
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
            tmp_file = path.join(hp.BASE_DIR, 'temp', 'cut', img_path)
            if not path.exists(path.dirname(tmp_file)):
                os.makedirs(path.dirname(tmp_file))
            img_obj.save(tmp_file)
            self.oss_web.upload_file(img_path, tmp_file)
            return tmp_file
        raise OSError('oss not exist or not writeable')


def extract_img(db=None, db_name=None, uri=None, condition=None, chars=None,
                regen=False, username=None, host=None):
    """ 从大图中切图，存放到web_img中，供web访问"""
    cfg = hp.load_config()
    db = db or uri and pymongo.MongoClient(uri)[db_name] or hp.connect_db(cfg['database'], db_name=db_name, host=host)[
        0]
    cut = Cut(db, cfg, regen=regen)

    print('[%s]extract_img.py script started.' % hp.get_date_time())
    if chars:
        print('[%s]%s chars to generate.' % (hp.get_date_time(), len(chars)))
        log = cut.cut_img(chars)
        update = None
        if log.get('cut_char_success'):
            update = {'has_img': True, 'img_need_updated': False, 'img_time': hp.get_date_time('%m%d%H%M%S')}
            db.char.update_many({'name': {'$in': log['cut_char_success']}}, {'$set': update})
        Bh.add_op_log(db, 'extract_img', 'finished', log, username)
        return update and update['img_time']

    condition = json.loads(condition) if isinstance(condition, str) else {}
    condition['img_need_updated'] = True

    once_size = 5000
    total_count = db.char.count_documents(condition)
    log_id = Bh.add_op_log(db, 'extract_img', 'ongoing', [], username)
    print('[%s]%s chars to generate.' % (hp.get_date_time(), total_count))
    while db.char.count_documents({'img_need_updated': True}):
        chars = list(db.char.find(condition).limit(once_size))
        log = cut.cut_img(chars)
        if log.get('cut_char_success'):
            update = {'has_img': True, 'img_need_updated': False, 'img_time': hp.get_date_time('%m%d%H%M%S')}
            db.char.update_many({'name': {'$in': log['cut_char_success']}}, {'$set': update})
        db.oplog.update_one({'_id': log_id}, {'$addToSet': {'content': log}})
    db.oplog.update_one({'_id': log_id}, {'$set': {'status': 'finished'}})


if __name__ == '__main__':
    import fire

    fire.Fire(extract_img)
