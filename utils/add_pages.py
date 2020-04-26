#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 导入页面文件到文档库，可导入页面图到 static/img 供本地调试用
# 本脚本的执行结果相当于在“数据管理-页数据”中提供了图片、OCR切分数据、文本，是任务管理中发布切分和文字审校任务的前置条件。
# python3 utils/add_pages.py --json_path=切分文件路径 [--img_path=页面图路径] [--txt_path=经文路径] [--kind=藏经类别码]

import re
import sys
import json
import shutil
import pymongo
from glob2 import glob
from tornado.util import PY3
from datetime import datetime
from os import path, listdir, makedirs, walk

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.helper import prop
from controller.data.data import Page
from controller.page.tool import PageTool
from controller.page.base import PageHandler


class AddPage(object):
    def __init__(self, db, source='', update=False, check_only=False, use_local_img=False,
                 check_id=False, reorder=None):
        self.db = db
        self.source = source
        self.update = update
        self.check_only = check_only
        self.use_local_img = use_local_img
        self.check_id = check_id
        self.reorder = reorder

    @staticmethod
    def load_json(filename):
        if not path.exists(filename):
            return
        try:
            with open(filename, encoding='UTF-8') if PY3 else open(filename) as f:
                return json.load(f)
        except Exception as e:
            sys.stderr.write('invalid file %s: %s\n' % (filename, str(e)))

    @staticmethod
    def check_ids(page):
        def check(m):
            return m and len(m[0]) == len([n for n in m[0] if 0 < int(n) < 150])

        for b in page.get('blocks'):
            b['block_id'] = b.get('block_id') or b.get('block_no') and 'b%d' % b['block_no'] or ''
            if not b['block_id'] and len(page['blocks']) == 1:
                b['block_id'] = 'b1'
                b['block_no'] = 1
            if not check(re.findall(r'^b(\d+)$', b.get('block_id'))):
                print('%s invalid block: %s' % (page['name'], str(b)))
                return False
        for c in page.get('columns'):
            if not check(re.findall(r'^b(\d+)c(\d+)$', c.get('column_id', ''))):
                print('%s invalid column: %s' % (page['name'], str(c)))
                return False
        for c in page.get('chars'):
            if not check(re.findall(r'^b(\d+)c(\d+)c(\d+)$', c.get('char_id', ''))):
                print('%s invalid column: %s' % (page['name'], str(c)))
                return False
        return True

    def add_text(self, pages, src_dir, field='ocr', update=False):
        """ 更新数据库page表的tex字段
        :param pages, 待更新的页面名称
        :param src_dir, 从该文件夹中查找
        :param field, 更新哪个字段
        :param update, 数据库中存在时，是否更新
        """
        if not path.exists(src_dir):
            return
        for root, dirs, files in walk(src_dir):
            for fn in files:
                if (fn.endswith('.ocr') or fn.endswith('.txt')) and fn[:-4] in pages:
                    cond = {'$or': [dict(name=fn[:-4]), dict(img_name=fn[:-4])]}
                    page = self.db.page.find_one(cond)
                    if not page:
                        continue
                    pathname = path.join(root, fn)
                    with open(pathname, encoding='UTF-8') if PY3 else open(pathname) as f:
                        text = f.read().strip().replace('\n', '|')
                    if not page.get('text') or update:
                        self.db.page.update_many(cond, {'$set': {field: re.sub(r'[<>]', '', text)}})

    @classmethod
    def copy_img_files(cls, pages, src_dir, update=False):
        """ 拷贝图片文件
        :param pages, 待拷贝的页面名称
        :param src_dir, 从该文件夹中查找
        :param update, 图片存在时，是否更新
        """
        if not path.exists(src_dir):
            return
        img_path = path.join(BASE_DIR, 'static', 'img')
        if not path.exists(img_path):
            makedirs(img_path)

        for root, dirs, files in walk(src_dir):
            for fn in files:
                if not fn.endswith('.jpg') or fn[:-4] not in pages:
                    continue
                dst_dir = path.join(img_path, fn[:2])
                if not path.exists(dst_dir):
                    makedirs(dst_dir)
                dst_file = path.join(dst_dir, fn)
                if not path.exists(dst_file) or update:
                    shutil.copy(path.join(root, fn), dst_file)

    @staticmethod
    def filter_line_no(boxes):
        for b in boxes:
            if b.get('line_no') and not b.get('column_no'):
                b['column_no'] = b.get('line_no')
            b.pop('line_no', 0)
        return boxes

    def add_box(self, name, info):
        """ 导入切分信息 """
        exist = self.db.page.find_one(dict(name=name))
        if self.check_only and exist:
            print('%s exist' % name)
            return
        if self.update or not exist:
            width = int(prop(info, 'imgsize.width') or prop(info, 'img_size.width') or prop(info, 'width') or 0)
            height = int(prop(info, 'imgsize.height') or prop(info, 'img_size.height') or prop(info, 'height') or 0)
            chars = self.filter_line_no(prop(info, 'chars', []))
            columns = self.filter_line_no(prop(info, 'columns', []))
            meta = Page.metadata()
            meta.update(dict(
                name=name, width=width, height=height, page_code=Page.name2pagecode(name),
                blocks=prop(info, 'blocks', []), columns=columns, chars=chars,
            ))
            if not width or not height:
                assert exist
                meta.pop('width')
                meta.pop('height')

            for field in ['source', 'create_time', 'ocr_col', 'img_name', 'char_ocr']:
                if info.get(field):
                    meta[field] = info[field]
            if info.get('ocr'):
                if isinstance(info['ocr'], list):
                    info['ocr'] = '|'.join(info['ocr']).replace('\u3000', '|').replace(' ', '')
                else:
                    info['ocr'] = info['ocr'].replace('\n', '|')
                meta['ocr'] = info['ocr'].replace(r'\|+', '|')
            if info.get('text'):
                if isinstance(info['text'], list):
                    info['text'] = '|'.join(info['text']).replace('\u3000', '|').replace(' ', '')
                else:
                    info['text'] = info['text'].replace('\n', '|')
                meta['text'] = info['text'].replace(r'\|+', '|')
            if info.get('text') == info.get('ocr'):
                info.pop('text', 0)
            if self.use_local_img:
                meta['use_local_img'] = True
            if self.source:
                meta['source'] = self.source
            layouts = ['上下一栏', '上下一栏', '上下两栏', '上下三栏']
            meta['layout'] = prop(info, 'layout') or layouts[len(info['blocks'])]

            PageHandler.update_chars_cid(meta['chars'])
            if self.check_id and not self.check_ids(meta):
                return False

            if self.check_only:
                return meta

            info.pop('id', 0)
            message = '%s:\t%d x %d blocks=%d columns=%d chars=%d'
            print(message % (name, width, height, len(meta['chars']), len(meta['columns']), len(meta['blocks'])))

            if self.reorder:
                meta['blocks'], meta['columns'], meta['chars'] = PageTool.reorder_boxes(page=meta)

            if exist and self.update:
                meta.pop('create_time', 0)
                r = self.db.page.update_one(dict(name=name), {'$set': meta})
                info['id'] = str(exist['_id'])
            else:
                if meta.get('create_time') and isinstance(meta['create_time'], str):
                    meta['create_time'] = datetime.strptime(meta['create_time'], '%Y-%m-%d %H:%M:%S')
                meta['create_time'] = prop(meta, 'create_time', datetime.now())
                r = self.db.page.insert_one(meta)
                info['id'] = str(r.inserted_id)

            return r

    def add_many_from_dir(self, src_dir, kind):
        """ 导入json格式的切分数据
        :param src_dir, 待导入的文件夹
        :param kind, 指定藏经类别
        """
        pages = set()
        for pathname in sorted(glob(path.join(src_dir, '**', '*.json'))):
            fn = path.basename(pathname)
            if kind and kind != fn[:2] or '_char' in fn:
                continue
            if fn[:-5] in pages:
                sys.stderr.write('duplicate page name %s \n' % pathname)
                continue
            info = self.load_json(pathname)
            if not info:
                sys.stderr.write('invalid json %s \n' % pathname)
                continue
            try:
                name = info.get('img_name') or info.get('imgname') or info.get('name')
                if not re.match(r'^[A-Z]{2}(_\d+)+$', name):
                    sys.stderr.write('invalid name in file %s \n' % pathname)
                    continue
                if name != fn[:-5]:
                    sys.stderr.write('filename not equal to name in json %s \n' % pathname)
                    continue
                if self.add_box(name, info):
                    pages.add(name)
            except Exception as e:
                sys.stderr.write('invalid page %s: %s \n' % (pathname, str(e)))
        return pages


def main(db=None, db_name='tripitaka', uri='localhost', json_path='', img_path='img', txt_path='txt',
         txt_field='ocr', kind='', source='', check_id=False, reorder=True, reset=True,
         use_local_img=False, update=False, check_only=False):
    """
    导入页面的主函数
    :param db: 数据库链接
    :param db_name: 数据库名
    :param uri: 数据库服务器的地址，可为localhost或mongodb://user:password@server
    :param json_path: 页面JSON文件的路径，如果遇到是两个大写字母的文件夹就视为藏别，json_path为空则取为data目录
    :param img_path: 页面图路径，json_path为空时取为data目录，可在不同的子目录下放图片文件(*.jpg)
    :param txt_path: 页面文本文件的路径，json_path为空时取为data目录，可在不同的子目录下放图片文件(*.txt)
    :param txt_field: 文本导入哪个字段
    :param kind: 可指定要导入的藏别
    :param source: 导入批次名称
    :param check_id: 是否检查切分框的id
    :param reorder: 是否重新计算序号
    :param reset: 是否先清空page表
    :param use_local_img: 是否强制使用本地的页面图，默认使用OSS上的高清图（如果在app.yml配置了OSS）
    :param update: 已存在的页面是否更新
    :param check_only: 是否仅校验数据而不插入数据
    :return: 新导入的页面的个数
    """
    if not db:
        db = pymongo.MongoClient(uri)[db_name]
    if reset:
        db.page.delete_many({})
    if not json_path:
        txt_path = json_path = img_path = path.join(BASE_DIR, 'meta', 'sample')

    add = AddPage(db, source, update, check_only, use_local_img, check_id, reorder)
    pages = add.add_many_from_dir(json_path, kind)
    add.copy_img_files(pages, img_path)
    add.add_text(pages, txt_path, txt_field)
    return 'add %s pages' % len(pages)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
