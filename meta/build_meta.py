#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import os.path as path
from functools import cmp_to_key
from meta.export_meta import get_date_time

META_DIR = path.join(path.dirname(__file__), 'meta')
db = ''


def cmp_code(a, b):
    al, bl = a.split('_'), b.split('_')
    if len(al) != len(bl):
        return len(al) - len(bl)
    for i in range(len(al)):
        length = max(len(al[i]), len(bl[i]))
        ai, bi = al[i].zfill(length), bl[i].zfill(length)
        if ai != bi:
            return 1 if ai > bi else -1
    return 0


def get_volume_info(tripitaka, root, volume, envelop=None):
    rows, content_pages, front_cover_pages, back_cover_pages = [], [], [], []
    volume_path = path.join(root, envelop, volume) if envelop else path.join(root, volume)
    for fn in os.listdir(volume_path):
        if path.isdir(path.join(root, volume, fn)) or fn.startswith('.'):
            continue
        page, suffix = fn.split('.', maxsplit=2)
        # 判断是否包含hash后缀
        page = page.split('_')[-2] if len(page.split('_')[-1]) > 6 else page.split('_')[-1]
        if 'f' in page:
            basename = 'f%s' % int(page.lstrip('f'))
            fullname = '%s_%s_%s_%s' % (tripitaka, int(envelop), int(volume), basename) if envelop else '%s_%s_%s' % (
                tripitaka, int(volume), basename)
            front_cover_pages.append(fullname)
        elif 'b' in page:
            basename = 'b%s' % int(page.lstrip('b'))
            fullname = '%s_%s_%s_%s' % (tripitaka, int(envelop), int(volume), basename) if envelop else '%s_%s_%s' % (
                tripitaka, int(volume), basename)
            back_cover_pages.append(fullname)
        else:
            basename = '%s' % int(page)
            fullname = '%s_%s_%s_%s' % (tripitaka, int(envelop), int(volume), basename) if envelop else '%s_%s_%s' % (
                tripitaka, int(volume), basename)
            content_pages.append(fullname)

    content_pages.sort(key=cmp_to_key(cmp_code))
    front_cover_pages.sort(key=cmp_to_key(cmp_code))
    back_cover_pages.sort(key=cmp_to_key(cmp_code))

    # volume_code, tripitaka_code, envelop_no, volume_no, content_pages, front_cover_pages, back_cover_pages,
    # remark, created_time, updated_time
    volume_code = '%s_%s_%s' % (tripitaka, int(envelop), int(volume)) if envelop else '%s_%s' % (tripitaka, int(volume))
    row = [volume_code, tripitaka, envelop, int(volume), content_pages or None, front_cover_pages or None,
           back_cover_pages or None, None, get_date_time(), get_date_time()]
    return row


def generate_volume_from_dir(tripitaka, root, level=1):
    """ 扫描藏经文件夹，生成存储结构信息
    :param tripitaka 藏经代码，如JX/GL等等
    :param root 待扫描的藏经文件目录
    :param level 图片的存储层次，如果是【藏-册-页】模式，则存储层次为1，如为【藏-函-册-页】【藏-经-卷-页】模式，则层次为2
    """
    assert level in [1, 2]
    fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_pages', 'front_cover_pages',
              'back_cover_pages', 'remark', 'created_time', 'updated_time']
    rows = []
    if level == 1:
        for volume in os.listdir(root):
            if path.isdir(path.join(root, volume)):
                rows.append(get_volume_info(tripitaka, root, volume))
    elif level == 2:
        for envolop in os.listdir(root):
            if path.isfile(path.join(root, envolop)):
                continue
            for volume in os.listdir(path.join(root, envolop)):
                rows.append(get_volume_info(tripitaka, root, volume, envolop))

    with open(path.join('./Volume-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        writer.writerow(fields)
        writer.writerows(rows)


if __name__ == '__main__':
    root = '/Volumes/tripitaka2/big/LC'
    generate_volume_from_dir('LC', root, 2)
    print('finished!')
