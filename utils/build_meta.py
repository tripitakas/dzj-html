#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 根目录：藏经目录的上一层目录。
#       比如对于网盘目录/srv/nextcloud/data/xxxx/files/YY来讲，
#       藏经目录是YY，根目录是YY的上一层，即/srv/nextcloud/data/xxxx/files
# 存储层次：指的是文件夹或文件相对根目录的距离。
#       比如/srv/nextcloud/data/xxxx/files/YY/1-永乐北藏/1-大般若经/1/1.jpg
#       其中，YY的存储层次为1，1-永乐北藏的存储层次为2，1-大般若经的存储层次为3，1.jpg的存储层次为4
#       注意：一部藏经内或者一个组织机构的文件夹中，文件的存储层次必须是一致的！
# 存储深度：指的是待导入的文件夹中，文件的最大存储层次。
#       比如【藏-册-页】【藏-经-页】的模式，存储深度为3，【藏-函-册-页】【藏-经-卷-页】的模式，存储深度为4。
# 函数功能：导入图片文件至工作目录，并提取对应的册、页基础数据，经、卷基础数据视情况提取。
#       如果存储深度是3且文件夹名中带有中文，则可提取经信息。
#       如果存储深度是4且文件夹名中带有中文，则可提取经和卷信息。
# 说明:  网盘用户的根目录有固定格式，程序自动从导入目录的路径中获取。非网盘用户，手工指定即可。

import re
import os
import csv
import json
import shutil
from os import path
from glob2 import glob
from functools import reduce
from functools import cmp_to_key
from collections import Counter
from datetime import datetime, timedelta

tripitaka_code_not_existed = 1000, '藏经或组织机构代码不存在'
tripitaka_code_error = 1001, '藏经或组织机构代码格式有误'
name_format_error = 1002, '命名格式有误'
store_level_error = 1003, '文件存储层次有误'

WORK_DIR = '/tripitakas/big'


def get_import_base(import_dir):
    """ 获取网盘用户待导入目录的根目录
    网盘用户目录有规范结构，如'/srv/nextcloud/data/zhangsan/files/LQ/1-正法明目'
    其中，zhangsan是用户名，LQ是藏经代码或机构代码，根目录为/srv/nextcloud/data/zhangsan/files'
    """
    regex_of_pan_user = r'(/srv/nextcloud/data/[^\/]+/files/)([A-Z]{2})(-.*)?/(.*)'
    m = re.match(regex_of_pan_user, import_dir)
    return m and m.group(1)


def build(import_dir, import_base='', work_dir='', force=False):
    """ 生成基础数据
    :param import_base 藏经文件所在的根目录，即藏经文件夹的上一层目录
    :param import_dir 导入的源目录
    :param work_dir 导入的目的目录
    :param force 图片存在是是否覆盖
    """
    # 初始化参数
    work_dir = WORK_DIR if not work_dir else work_dir
    work_dir = work_dir.rstrip('/') + '/'
    import_base = get_import_base(import_dir) if not import_base else import_base
    import_base = import_base.rstrip('/') + '/'

    # 检查藏经或组织机构代码
    # r = is_tripitaka_code_existed(import_dir)
    # if r is not True:
    #     return r

    # 检查文件夹和文件命名规范
    r = check_valid(import_base, import_dir)
    if r is not True:
        return r

    # # 生成基础数据
    gen_volumes(import_base, import_dir)
    gen_sutras(import_base, import_dir)
    gen_reels(import_base, import_dir)

    # 拷贝导入目录至工作目录并重命名
    copy_and_rename(import_base, import_dir, work_dir, force=force)

    # 生成页面基础数据
    gen_pages(import_base, import_dir, work_dir)


def check_valid(base, import_dir):
    """ 检查目录及文件命名是否符合规范，文件存储结构是否一致
    :return True/错误代码。如果有误，则在import_dir下生成错误文件，类似errors-201910251832.csv
    """
    errors, depth = [], get_depth(base, import_dir)

    # 校验import_dir的命名规范
    regex = '%s(-.+)*$' % ('[A-Z]{2}' if get_level(base, import_dir) == 1 else r'\d+')
    if not re.match(regex, path.basename(import_dir)):
        errors.append([import_dir, name_format_error[1]])

    for root, dirs, files in os.walk(import_dir, topdown=True):
        for dir in dirs:
            # 检查文件夹命名格式，有三种：1/1-房山石经/1-房山石经-大般若经
            if dir[0] in '._':
                continue
            if not re.match(r'\d+(-.+)*$', dir):
                errors.append([path.join(root, dir), name_format_error[1]])
        for filename in files:
            # 检查文件的存储层次
            if filename[0] in '._':
                continue
            if depth != get_level(base, path.join(root, filename)):
                errors.append([path.join(root, filename), store_level_error[1]])
            # 检查文件名格式：忽略非图片，图片文件名只能是数字或fb字母
            if re.match(r'.*.(jpg|png|tif|gif)', filename) and not re.match(r'[0-9fb]+.(jpg|png|tif|gif)', filename):
                errors.append([path.join(root, filename), name_format_error[1]])

    # 生成错误文件
    if errors:
        filename = path.join(import_dir, '_errors-%s.csv' % datetime.now().strftime('%Y%m%d%H%M'))
        with open(filename, 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(['文件或文件夹', '错误信息'])
            writer.writerows(errors)

    return False if errors else True


def gen_volumes(base, import_dir):
    """ 生成册信息csv文件，文件存放在import_dir/volume.csv中。"""
    volumes = []
    fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_page_count', 'content_pages',
              'front_cover_pages', 'back_cover_pages', 'remark', 'create_time', 'updated_time']
    depth = get_depth(base, import_dir)
    tripitaka = get_tripitaka_code(base, import_dir)
    args = [base, tripitaka, '*', '*'] if depth == 4 else [base, tripitaka, '*']
    for volume_path in glob(path.join(*args)):
        if path.basename(volume_path)[0] in '._':
            continue
        volume = volume_path.split('/')[-1]
        envelop = volume_path.split('/')[-2] if depth == 4 else ''
        volumes.append(get_volume(base, tripitaka, volume, envelop))

    # 保存文件
    if volumes:
        volumes.sort(key=cmp_to_key(cmp_volume))
        filename = path.join(import_dir, '_volumes-%s.csv' % datetime.now().strftime('%Y%m%d%H%M'))
        with open(filename, 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(fields)
            writer.writerows(volumes)


def get_volume(base, tripitaka, volume, envelop=''):
    rows, content_pages, front_cover_pages, back_cover_pages = [], [], [], []
    volume_path = path.join(base, tripitaka, envelop, volume)
    for filename in sorted(os.listdir(volume_path)):
        ext = filename.split('.')[-1].lower()
        filepath = path.join(volume_path, filename)
        if filename[0] in '._~' or path.isdir(filepath) or ext not in ['jpg', 'png', 'tif', 'gif']:
            continue
        page, suffix = filename.split('.', maxsplit=2)
        # 判断是否包含hash后缀
        parts = page.split('_')
        page = parts[-2] if len(parts) > 1 and len(parts[-1]) > 6 else parts[-1]
        if 'f' in page:  # 封面: 末尾一个数前有f
            basename = 'f%s' % int(page.lstrip('f'))
            fn = '%s%s_%s_%s' % (tripitaka, '_%s' % pick_int(envelop) if envelop else '', pick_int(volume), basename)
            front_cover_pages.append(fn)
        elif 'b' in page:  # 封底: 末尾一个数前有b
            basename = 'b%s' % int(page.lstrip('b'))
            fn = '%s%s_%s_%s' % (tripitaka, '_%s' % pick_int(envelop) if envelop else '', pick_int(volume), basename)
            back_cover_pages.append(fn)
        else:  # 序或正文
            basename = '%s' % pick_int(page)
            fn = '%s%s_%s_%s' % (tripitaka, '_%s' % pick_int(envelop) if envelop else '', pick_int(volume), basename)
            content_pages.append(fn)

    content_pages.sort(key=cmp_to_key(cmp_code))
    front_cover_pages.sort(key=cmp_to_key(cmp_code))
    back_cover_pages.sort(key=cmp_to_key(cmp_code))

    # volume_code, tripitaka_code, envelop_no, volume_no, content_page_count, content_pages,
    # front_cover_pages, back_cover_pages, remark, create_time, updated_time
    volume_code = '%s%s_%s' % (tripitaka, '_%s' % pick_int(envelop) if envelop else '', pick_int(volume))
    remark = '%s%s' % (envelop + '#' if envelop else '', volume)
    row = [volume_code, tripitaka, pick_int(envelop), pick_int(volume), len(content_pages),
           content_pages or None, front_cover_pages or None, back_cover_pages or None,
           remark, get_date_time(), get_date_time()]
    return row


def gen_sutras(base, import_dir):
    """ 生成卷信息csv文件，文件存放在import_dir/_sutras.csv中。 """
    sutras = []
    fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'due_reel_count', 'existed_reel_count', 'author',
              'trans_time', 'start_volume', 'start_page', 'end_volume', 'end_page', 'remark']
    depth = get_depth(base, import_dir)
    assert depth in [3, 4]
    tripitaka = get_tripitaka_code(base, import_dir)
    args = [base, tripitaka, '*']
    for sutra_path in glob(path.join(*args)):
        if path.basename(sutra_path)[0] in '._':
            continue
        sutra = sutra_path.split('/')[-1]
        if len(sutra.split('-')) == 1:
            continue
        sutra_name = '-'.join(sutra.split('-')[1:])
        sutra_code = '%s%04d' % (tripitaka, pick_int(sutra))
        if depth == 4:
            reels = [r for r in os.listdir(sutra_path) if path.isdir(path.join(sutra_path, r))]
            reels.sort(key=cmp_to_key(lambda a, b: pick_int(a) - pick_int(b)))
            start_volume = '%s_%s_%s' % (tripitaka, pick_int(sutra), pick_int(reels[0]))
            start_volume_path = path.join(sutra_path, str(reels[0]))
            start_volume_pages = sorted([int(p.split('.')[0].split('-')[-1]) for p in os.listdir(start_volume_path)
                                         if re.match(r'\d+.(jpg|png|tif|gif)', p)])
            end_volume = '%s_%s_%s' % (tripitaka, pick_int(sutra), pick_int(reels[-1]))
            end_volume_path = path.join(sutra_path, str(reels[-1]))
            end_volume_pages = sorted([int(p.split('.')[0].split('-')[-1]) for p in os.listdir(end_volume_path)
                                       if re.match(r'\d+.(jpg|png|tif|gif)', p)])
            sutras.append(['', sutra_code, sutra_name, pick_int(reels[-1]), len(reels), '', '',
                           start_volume, start_volume_pages[0] if start_volume_pages else None,
                           end_volume, end_volume_pages[-1] if end_volume_pages else None, ''])
        else:
            pages = sorted([int(p.split('.')[0].split('-')[-1]) for p in os.listdir(sutra_path)
                            if re.match(r'\d+.(jpg|png|tif|gif)', p)])
            start_volume = end_volume = '%s_%s' % (tripitaka, pick_int(sutra))
            sutras.append(['', sutra_code, sutra_name, 1, 1, '', '', start_volume, pages[0], end_volume, pages[-1], ''])

    # 保存文件
    if sutras:
        sutras.sort(key=cmp_to_key(cmp_sutra))
        filename = path.join(import_dir, '_sutras-%s.csv' % datetime.now().strftime('%Y%m%d%H%M'))
        with open(filename, 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(fields)
            writer.writerows(sutras)


def gen_reels(base, import_dir):
    """ 生成卷信息csv文件，文件存放在import_dir/_reels.csv中。 """
    reels = []
    fields = ['uni_sutra_code', 'sutra_code', 'sutra_name', 'reel_code', 'reel_no', 'start_volume', 'start_page',
              'end_volume', 'end_page', 'remark']
    depth = get_depth(base, import_dir)
    assert depth == 4  # 只有【藏-经-卷-页】时才有卷信息，存储深度应为4
    tripitaka = get_tripitaka_code(base, import_dir)
    args = [base, tripitaka, '*', '*']
    for reel_path in glob(path.join(*args)):
        if path.basename(reel_path)[0] in '._':
            continue
        reel = reel_path.split('/')[-1]
        sutra = reel_path.split('/')[-2]
        sutra_name = '-'.join(sutra.split('-')[1:])
        if len(sutra.split('-')) == 1:
            continue
        sutra_code = '%s%04d' % (tripitaka, pick_int(sutra))
        reel_code = '%s_%d' % (sutra_code, pick_int(reel))
        start_volume = end_volume = '%s_%s_%s' % (tripitaka, pick_int(sutra), pick_int(reel))
        pages = sorted([int(p.split('.')[0].split('-')[-1]) for p in os.listdir(reel_path)
                        if re.match(r'\d+.(jpg|png|tif|gif)', p)])
        reels.append(['', sutra_code, sutra_name, reel_code, pick_int(reel), start_volume,
                      pages[0] if pages else None, end_volume, pages[-1] if pages else None, ''])

    # 保存文件
    if reels:
        reels.sort(key=cmp_to_key(cmp_reel))
        filename = path.join(import_dir, '_reels-%s.csv' % datetime.now().strftime('%Y%m%d%H%M'))
        with open(filename, 'w', newline='') as fn:
            writer = csv.writer(fn)
            writer.writerow(fields)
            writer.writerows(reels)


def gen_pages(base, import_dir, work_dir, suffix=''):
    """ 生成页面名称的json文件。
    从src_dir下读页面文件，结果存放在dst_dir下page.json文件中。
    """

    def get_base_name(fullname):
        return path.basename(fullname).split('.')[0]

    # 读取页面文件名
    tripitaka = get_tripitaka_code(base, import_dir)
    mid_dir = import_dir.replace(base, '').split('/')[1:]  # 去掉第一个藏经代码
    mid_dir = [str(pick_int(r)) for r in mid_dir]
    pages_dir = path.join(work_dir, tripitaka, '/'.join(mid_dir))
    suffix = suffix if suffix else get_suffix(import_dir)
    pages = [get_base_name(img) for img in glob(path.join(pages_dir, '**', '*.%s' % suffix))
             if '_f' not in get_base_name(img) and '_b' not in get_base_name(img)]
    pages.sort(key=cmp_to_key(cmp_code))

    # 保存文件
    filename = path.join(import_dir, '_pages-%s.json' % datetime.now().strftime('%Y%m%d%H%M'))
    with open(filename, 'w') as fn:
        fn.write(json.dumps(pages))


def copy_and_rename(base, import_dir, work_dir, force=False):
    """ 将文件夹拷贝到工作目录，并且按照规范格式重命名 """
    tripitaka = get_tripitaka_code(base, import_dir)
    for root, dirs, files in os.walk(import_dir, topdown=True):
        for dir in dirs:
            mid_dir = path.join(root, dir).replace(base, '').split('/')[1:]  # 去掉第一个藏经代码
            mid_dir = [str(pick_int(r)) for r in mid_dir]
            to_dir = path.join(tripitaka, '/'.join(mid_dir))
            if not path.exists(to_dir):
                os.makedirs(to_dir)
        for filename in files:
            if filename.split('.')[-1] not in ['jpg', 'png', 'tif', 'gif']:
                continue
            mid_dir = root.replace(base, '').split('/')[1:]
            mid_dir = [str(pick_int(r)) for r in mid_dir]
            to_dir = path.join(work_dir, tripitaka, *mid_dir)
            if not path.exists(to_dir):
                os.makedirs(to_dir)
            to_file = path.join(to_dir, '%s_%s_%s' % (tripitaka, '_'.join(mid_dir), filename))
            if force or not path.exists(to_file):
                shutil.copy(path.join(root, filename), to_file)


def get_tripitaka_code(base, import_dir):
    """ 获取导入目录的藏经代码，base目录的下一层为藏经代码"""
    relative_path = import_dir.replace(base, '').lstrip('/')
    return relative_path.split('/')[0].split('-')[0]


def get_depth(base, import_dir, suffix=''):
    """ 获取导入目录的存储深度 """
    # 随机挑选几张图片，计算存储深度
    suffix = suffix if suffix else get_suffix(import_dir)
    imgs = glob(path.join(import_dir, '**', '*.%s' % suffix))
    assert imgs
    levels = [len(img.replace(base, '').split('/')) for img in imgs[:10]]
    level = Counter(levels).most_common(1)[0][0]
    return level


def get_suffix(import_dir):
    """" 获取图片后缀 """
    for suffix in ['jpg', 'png', 'tif', 'gif']:
        if glob(path.join(import_dir, '**', '*.%s' % suffix)):
            return suffix


def get_level(base, dir_or_file):
    """ 获取任意文件或文件夹的存储层次"""
    level = len(dir_or_file.replace(base, '').split('/'))
    return level


def cmp_code(a, b):
    al, bl = a.split('_'), b.split('_')
    length = max(len(al), len(bl))
    for i in range(length):
        ai = (al[i] if i < len(al) else '').zfill(length)
        bi = (bl[i] if i < len(bl) else '').zfill(length)
        if ai != bi:
            return 1 if ai > bi else -1
    return 0


def cmp_volume(a, b):
    return cmp_code(a[0], b[0])


def cmp_sutra(a, b):
    return cmp_code(a[1], b[1])


def cmp_reel(a, b):
    return cmp_code(a[3], b[3])


def pick_int(s):
    return s.split('-')[0] and int(s.split('-')[0])


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


if __name__ == '__main__':
    import fire

    fire.Fire(build)
    print('finished!')
