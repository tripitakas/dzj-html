#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 对指定的页面，从OSS上的原图提取单字图和列图，并将生成的图上传到OSS。
@time: 2020-02-25
"""

import re
import json
import logging
import hashlib
import shutil
from os import path, makedirs, remove
from glob2 import glob
from PIL import Image
from boto3.session import Session
from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError
from controller.helper import BASE_DIR, load_config, connect_db


def get_img_key(img_name, salt, cid=''):
    img_name += '_' + cid if cid else ''
    md5 = hashlib.md5()
    md5.update((img_name + salt).encode('utf-8'))
    new_name = '%s_%s.jpg' % (img_name, md5.hexdigest())
    return '/'.join(img_name.split('_')[:-1] + [new_name])


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


def extract_one_page(db, name, s3_big, s3_cut, salt, tmp_path, page_chars=None, regen=False):
    def upload_file(filename, bucket, key_):
        if isinstance(s3_cut, str):
            dst_file = path.join(s3_cut, bucket, '_'.join(key_.split('_')[:-1]) + '.jpg')
            if not path.exists(path.dirname(dst_file)):
                makedirs(path.dirname(dst_file))
            shutil.move(filename, dst_file)
        else:
            s3_cut.meta.client.upload_file(filename, bucket, key_)

    key = get_img_key(name, salt)
    down_file = path.join(tmp_path, '%s.jpg' % name)
    if not path.exists(down_file):
        if isinstance(s3_big, str):
            down_file = [f for f in glob(path.join(s3_big, *(name.split('_')[:-1]), name + '.*'))
                         if f.lower().split('.')[-1] in ['jpg', 'png', 'gif']]
            if not down_file:
                raise OSError('%s not exist in %s' % (name, s3_big))
            down_file = down_file[0]
        else:
            s3_big.meta.client.download_file('pages', key, down_file)
            logging.info('download_file: %s, %.1f kb' % (name, path.getsize(down_file) / 1024))

    page = db.page.find_one({'name': name})
    if not page:
        raise OSError('%s not found' % name)

    img = Image.open(down_file).convert('L')
    if img is None:
        raise OSError('fail to open %s' % down_file)
    w, h = img.size
    if w != page['width'] or h != page['height']:
        img = img.resize((page['width'], page['height']), Image.BICUBIC)

    if not isinstance(s3_big, str):
        remove(down_file)

    chars_done, columns_todo = [], set()
    chars_todo = page_chars or page['chars']
    for c in chars_todo:
        oc = page_chars and [oc for oc in page['chars'] if oc['cid'] == c['cid']]
        oc = oc and oc[0]
        if oc and c['has_img'] and not regen and dict(x=oc['x'], y=oc['y'], w=oc['w'], h=oc['h']) == c['pos']:
            continue
        oc = c['pos']
        try:
            img_c = img.crop((oc['x'], oc['y'], min(w, oc['x'] + oc['w']), min(h, oc['y'] + oc['h'])))
            img_c = resize_binary(img_c, 64, 64, True)
            img_file = path.join(tmp_path, '%s.jpg' % c['cid'])
            img_c.save(img_file)
            key = get_img_key(name, salt, str(c['cid']))
            upload_file(img_file, 'chars', key)
            chars_done.append(c['id'])
            columns_todo.add(c['column_cid'])
        except SystemError:
            continue
    if chars_done:
        db.char.update_many({'id': {'$in': chars_done}}, {'$set': {'has_img': True, 'img_need_updated': False}})
    logging.info('%s: %d char-images uploaded' % (name, len(chars_done)))

    columns_done = []
    columns_todo = list(columns_todo)
    columns_todo = [c for c in page['columns'] if c['cid'] in columns_todo]
    for c in columns_todo:
        try:
            img_c = img.crop((oc['x'], oc['y'], min(w, oc['x'] + oc['w']), min(h, oc['y'] + oc['h'])))
            img_c = resize_binary(img_c, 200, 800)
            img_file = path.join(tmp_path, '%s.jpg' % c['cid'])
            img_c.save(img_file)
            key = get_img_key(name, salt, str(c['cid']))
            upload_file(img_file, 'columns', key)
            columns_done.append(c['cid'])
        except SystemError:
            continue
    logging.info('%s: %d column-images uploaded' % (name, len(columns_done)))

    return dict(name=name, chars_count=len(chars_done), columns_count=len(columns_done))


def extract_cut_img(db=None, collection='char', char_condition=None, name=None, regen=False):
    assert collection in ['char', 'page']
    cfg = load_config()
    db = db or connect_db(cfg['database'])[0]

    oss = cfg['img']
    host_big = re.sub('tripitaka-[a-z]+', 'tripitaka-big', oss['host'])
    host_cut = re.sub('tripitaka-[a-z]+', oss['bucket'], oss['host'])

    tmp_path = path.join(BASE_DIR, 'log', 'img')
    if not path.exists(tmp_path):
        makedirs(tmp_path)

    chars = []
    if collection == 'char':
        cond = char_condition if char_condition else {'page_name': name} if name else {'img_need_updated': True}
        cond = json.loads(cond) if isinstance(cond, str) else cond
        chars = list(db.char.find(cond))
        page_names = set(c['page_name'] for c in chars)

    session = Session(aws_access_key_id=oss['access_key'], aws_secret_access_key=oss['secret_key'])
    s3_big = oss.get('big_path') or session.resource('s3', endpoint_url=host_big)
    s3_cut = oss.get('img_path') or session.resource('s3', endpoint_url=host_cut)
    res = dict(ok=[], fail=[])
    for name in page_names:
        try:
            page_chars = [c for c in chars if c['page_name'] == name]
            res['ok'].append(extract_one_page(db, name, s3_big, s3_cut, oss['salt'], tmp_path, page_chars, regen=regen))
        except (Boto3Error, BotoCoreError):
            res['fail'].append(dict(name=name, message='OSS Error'))
        except Exception as e:
            res['fail'].append(dict(name=name, message='[%s] %s' % (e.__class__.__name__, str(e))))
    return res


if __name__ == '__main__':
    import fire

    fire.Fire(extract_cut_img)
    # print(extract_cut_img(name='GL_1047_1_5', regen=True))
