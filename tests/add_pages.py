#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 导入页面文件到文档库，可导入页面图到 static/img 供本地调试用
# 本脚本的执行结果相当于在“数据管理-页数据”中提供了图片、OCR切分数据、文本，是任务管理中发布切分和文字审校任务的前置条件。
# python tests/add_pages.py --json_path=切分文件路径 [--img_path=页面图路径] [--txt_path=经文路径] [--kind=藏经类别码]

import sys
import os
import json
import re
import shutil
import pymongo
from tornado.util import PY3
from datetime import datetime
from os import path, listdir, mkdir

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from controller.task.base import TaskHandler as task

IMG_PATH = path.join(path.dirname(__file__), '..', 'static', 'img')
data = dict(count=0)

base_fields = {
    'str': ['name', 'kind', 'width', 'height', 'ocr', 'cmp1', 'txt1_html', 'cmp2', 'txt2_html',
            'cmp3', 'txt3_html', 'txt_html', 'text', 'create_time'],
    'list': ['blocks', 'columns', 'chars'],
    'dict': ['lock', 'tasks'],
}

task_types = [
    'block_cut_proof', 'block_cut_review', 'column_cut_proof', 'column_cut_review', 'char_cut_proof',
    'char_cut_review', 'text_proof_1', 'text_proof_2', 'text_proof_3', 'text_review', 'text_hard'
]


def create_folder(filename):
    if not path.exists(filename):
        mkdir(filename)


def open_file(filename):
    return open(filename, encoding='UTF-8') if PY3 else open(filename)


def load_json(filename):
    if path.exists(filename):
        try:
            with open_file(filename) as f:
                return json.load(f)
        except Exception as e:
            sys.stderr.write('invalid file %s: %s\n' % (filename, str(e)))


def scan_dir(src_path, kind, db, ret, repeat=0, use_local_img=False):
    if not path.exists(src_path):
        sys.stderr.write('%s not exist\n' % (src_path,))
        return []
    for fn in sorted(listdir(src_path)):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            fn2 = fn if re.match(r'^[A-Z]{2}$', fn) else kind
            if not kind or kind == fn2:
                scan_dir(filename, fn2, db, ret, repeat=repeat, use_local_img=use_local_img)
        elif kind and fn[:2] == kind:
            if fn.endswith('.json') and fn[:-5] not in ret:  # 相同名称的页面只导入一次
                info = load_json(filename)
                if info:
                    name = info.get('imgname')
                    if name != fn[:-5]:
                        sys.stderr.write('invalid imgname %s, %s\n' % (filename, kind))
                        continue
                    if repeat > 1:
                        add_repeat_pages(name, info, db, repeat, use_local_img=use_local_img)
                    else:
                        add_page(name, info, db, use_local_img=use_local_img)
                    ret.add(name)


def add_repeat_pages(name, info, db, repeat, use_local_img=False):
    """ 批量插入重复页面 """
    if not db.page.find_one(dict(name=name)):
        start, length = 1, 5000
        while start + length - 1 < repeat:
            _add_repeat_pages(name, info, db, start, start + length - 1, use_local_img)
            start += length
        _add_repeat_pages(name, info, db, start, repeat, use_local_img)


def _add_repeat_pages(name, info, db, start, end, use_local_img):
    meta_list = []
    for i in range(start, end + 1):
        meta = {k: '' for k in base_fields['str']}
        meta.update({k: {} for k in base_fields['dict']})
        meta.update({k: [] for k in base_fields['list']})
        meta.update(dict(
            name='%s_%s' % (name, i),
            img_name=name,
            kind=name[:2],
            width=int(info['imgsize']['width']),
            height=int(info['imgsize']['height']),
            blocks=info.get('blocks', []),
            columns=info.get('columns', []),
            chars=info.get('chars', []),
            create_time=datetime.now()
        ))
        if use_local_img:
            meta['use_local_img'] = True
        # initialize tasks
        meta.update(dict(tasks={t: dict(status=task.STATUS_READY) for t in task_types}))
        meta_list.append(meta)
    db.page.insert_many(meta_list)

    data['count'] += end - start + 1
    print('%s[%d:%d]:\t\t%d x %d blocks=%d columns=%d chars=%d' % (
        name, start, end, meta['width'], meta['height'], len(meta['blocks']), len(meta['columns']),
        len(meta['chars']),
    ))


def add_page(name, info, db, img_name=None, use_local_img=False):
    if not db.page.find_one(dict(name=name)):
        meta = {k: '' for k in base_fields['str']}
        meta.update({k: {} for k in base_fields['dict']})
        meta.update({k: [] for k in base_fields['list']})
        meta.update(dict(
            name=name,
            kind=name[:2],
            width=int(info['imgsize']['width']),
            height=int(info['imgsize']['height']),
            blocks=info.get('blocks', []),
            columns=info.get('columns', []),
            chars=info.get('chars', []),
            create_time=datetime.now()
        ))
        if img_name:
            meta['img_name'] = img_name
        if use_local_img:
            meta['use_local_img'] = True
        # initialize tasks
        meta.update(dict(tasks={t: dict(status=task.STATUS_READY) for t in task_types}))
        data['count'] += 1
        print('%s:\t%d x %d blocks=%d colums=%d chars=%d' % (
            name, meta['width'], meta['height'], len(meta['blocks']), len(meta['columns']), len(meta['chars'])))
        db.page.insert_one(meta)


def add_texts(src_path, pages, db):
    if not path.exists(src_path):
        return
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            add_texts(filename, pages, db)
        elif (fn.endswith('.ocr') or fn.endswith('.txt')) and fn[:-4] in pages:
            with open_file(filename) as f:
                text = f.read().strip().replace('\n', '|')
            cond = {'$or': [dict(name=fn[:-4]), dict(img_name=fn[:-4])]}
            r = list(db.page.find(cond))
            if r and not r[0].get('text'):
                db.page.update_many(cond, {'$set': dict(ocr=text)})


def copy_img_files(src_path, pages):
    if not path.exists(src_path):
        return
    create_folder(IMG_PATH)
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            copy_img_files(filename, pages)
        elif fn.endswith('.jpg') and fn[:-4] in pages:
            dst_file = path.join(IMG_PATH, fn[:2])
            create_folder(dst_file)
            dst_file = path.join(dst_file, fn)
            if not path.exists(dst_file):
                shutil.copy(filename, dst_file)


def main(json_path='', img_path='img', txt_path='txt', kind='', db_name='tripitaka', uri='localhost',
         reset=False, repeat=0, use_local_img=False):
    """
    页面导入的主函数
    :param json_path: 页面JSON文件的路径，如果遇到是两个大写字母的文件夹就视为藏别，json_path为空则取为data目录
    :param img_path: 页面图路径，json_path为空时取为data目录，可在不同的子目录下放图片文件(*.jpg)
    :param txt_path: 页面文本文件的路径，json_path为空时取为data目录，可在不同的子目录下放图片文件(*.txt)
    :param kind: 可指定要导入的藏别
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param reset: 是否先清空page表
    :param repeat: 页面重复次数，可用于模拟大量页面
    :param use_local_img: 是否让页面强制使用本地的页面图，默认是使用OSS上的高清图（如果在app.yml配置了OSS）
    :return: 新导入的页面的个数
    """
    if not json_path:
        txt_path = json_path = img_path = path.join(path.dirname(__file__), 'sample')
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    if reset:
        db.page.drop()
    pages = set()
    scan_dir(json_path, kind, db, pages, repeat=repeat, use_local_img=use_local_img)
    copy_img_files(img_path, pages)
    add_texts(txt_path, pages, db)
    return data['count']


if __name__ == '__main__':
    import fire

    fire.Fire(main)
