#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 导入页面文件到文档库，可导入页面图到 static/img 供本地调试用
# 本脚本的执行结果相当于在“数据管理-页数据”中提供了图片、OCR切分数据、文本，是任务管理中发布切分和文字审校任务的前置条件。
# python tests/add_pages.py --json_path=切分文件路径 [--img_path=页面图路径] [--txt_path=经文路径] [--kind=藏经类别码]

import sys
import os
import shutil
import pymongo
from os import path, listdir

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import controller.data.add_pages as add


def add_texts(src_path, pages, db):
    if not path.exists(src_path):
        return
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            add_texts(filename, pages, db)
        elif (fn.endswith('.ocr') or fn.endswith('.txt')) and fn[:-4] in pages:
            with add.open_file(filename) as f:
                text = f.read().strip().replace('\n', '|')
            cond = {'$or': [dict(name=fn[:-4]), dict(img_name=fn[:-4])]}
            r = list(db.page.find(cond))
            if r and not r[0].get('text'):
                db.page.update_many(cond, {'$set': dict(ocr=text)})


def copy_img_files(src_path, pages):
    if not path.exists(src_path):
        return
    add.create_folder(add.IMG_PATH)
    for fn in listdir(src_path):
        filename = path.join(src_path, fn)
        if path.isdir(filename):
            copy_img_files(filename, pages)
        elif fn.endswith('.jpg') and fn[:-4] in pages:
            dst_file = path.join(add.IMG_PATH, fn[:2])
            add.create_folder(dst_file)
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
    add.scan_dir(json_path, kind, db, pages, repeat=repeat, use_local_img=use_local_img)
    copy_img_files(img_path, pages)
    add_texts(txt_path, pages, db)
    return add.data['count']


if __name__ == '__main__':
    import fire

    fire.Fire(main)
