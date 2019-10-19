#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv
import shutil
import os.path as path
from functools import cmp_to_key
from datetime import datetime, timedelta

META_DIR = path.join(path.dirname(__file__), 'meta')
db = ''


def get_date_time(fmt=None, diff_seconds=None):
    time = datetime.now()
    if diff_seconds:
        time += timedelta(seconds=diff_seconds)
    return time.strftime(fmt or '%Y-%m-%d %H:%M:%S')


def cmp_code(a, b):
    al, bl = a.split('_'), b.split('_')
    length = max(len(al), len(bl))
    for i in range(length):
        ai = (al[i] if i < len(al) else '').zfill(length)
        bi = (bl[i] if i < len(bl) else '').zfill(length)
        if ai != bi:
            return 1 if ai > bi else -1
    return 0


def pick_int(s):
    return int(s.split('-')[0])


def get_volume_info(tripitaka, root, volume, envelop=None):
    rows, content_pages, front_cover_pages, back_cover_pages = [], [], [], []
    volume_path = path.join(root, envelop, volume) if envelop else path.join(root, volume)
    for fn in sorted(os.listdir(volume_path)):
        if fn.startswith('.') or path.isdir(path.join(root, volume, fn)) or fn.endswith('.json'):
            continue
        page, suffix = fn.split('.', maxsplit=2)
        # 判断是否包含hash后缀
        parts = page.split('_')
        page = parts[-2] if len(parts) > 1 and len(parts[-1]) > 6 else parts[-1]
        if 'f' in page:  # 封面: 末尾一个数前有f
            basename = 'f%s' % int(page.lstrip('f'))
            fullname = '%s_%s_%s_%s' % (tripitaka, pick_int(envelop), pick_int(volume), basename
                                        ) if envelop else '%s_%s_%s' % (tripitaka, pick_int(volume), basename)
            front_cover_pages.append(fullname)
        elif 'b' in page:  # 封底: 末尾一个数前有b
            basename = 'b%s' % int(page.lstrip('b'))
            fullname = '%s_%s_%s_%s' % (tripitaka, pick_int(envelop), pick_int(volume), basename
                                        ) if envelop else '%s_%s_%s' % (tripitaka, pick_int(volume), basename)
            back_cover_pages.append(fullname)
        else:  # 序或正文
            basename = '%s' % pick_int(page)
            fullname = '%s_%s_%s_%s' % (tripitaka, pick_int(envelop), pick_int(volume), basename
                                        ) if envelop else '%s_%s_%s' % (tripitaka, pick_int(volume), basename)
            content_pages.append(fullname)

    content_pages.sort(key=cmp_to_key(cmp_code))
    front_cover_pages.sort(key=cmp_to_key(cmp_code))
    back_cover_pages.sort(key=cmp_to_key(cmp_code))

    # volume_code, tripitaka_code, envelop_no, volume_no, content_page_count, content_pages, front_cover_pages,
    # back_cover_pages, remark, create_time, updated_time
    volume_code = '%s_%s_%s' % (tripitaka, pick_int(envelop), pick_int(volume)
                                ) if envelop else '%s_%s' % (tripitaka, pick_int(volume))
    row = [volume_code, tripitaka, pick_int(envelop), pick_int(volume),
           content_pages and len(content_pages) or 0, content_pages or None,
           front_cover_pages or None, back_cover_pages or None,
           (envelop and '-' in envelop and envelop.split('-')[-1] + ' ' or '') +
           (volume and '-' in volume and '-'.join(volume and volume.split('-')[1:]) or None),
           get_date_time(), get_date_time()]
    return row


def generate_volume_from_dir(tripitaka='LQ', root='/Users/zyg/Desktop/lq/tripitaka-web/static/upload/正法明目/LQ', level=2,
                             reorder_dir='', gen_sutra=True):
    """ 扫描藏经文件夹，生成存储结构信息
    :param tripitaka 藏经代码，如JX/GL等等
    :param root 待扫描的藏经文件目录，其中封面和封底的文件名最后一个数前有f或b
    :param level 图片的存储层次，如果是【藏-册-页】模式，则存储层次为1，如为【藏-函-册-页】【藏-经-卷-页】模式，则层次为2
    :param reorder_dir 是否重新对文件编号，是则指定输出目录
    :param gen_sutra 是否生成经目文件 Sutra-*.csv
    """
    if reorder_dir:
        return reorder_files(root, reorder_dir, tripitaka)
    assert level in [1, 2]
    fields = ['volume_code', 'tripitaka_code', 'envelop_no', 'volume_no', 'content_page_count', 'content_pages',
              'front_cover_pages', 'back_cover_pages', 'remark', 'create_time', 'updated_time']
    rows = []
    sutras, reels = [], []
    if level == 1:
        for volume in sorted(os.listdir(root)):
            if not volume.startswith('.') and path.isdir(path.join(root, volume)):
                rows.append(get_volume_info(tripitaka, root, volume))
    elif level == 2:
        for envolop in sorted(os.listdir(root)):
            if envolop.startswith('.') or path.isfile(path.join(root, envolop)):
                continue
            sutra = dict(sutra_code='%s%04d' % (tripitaka, pick_int(envolop)),
                         sutra_name=envolop.split('-')[-1],
                         due_reel_count=0)
            reel = dict(sutra_code='%s%04d' % (tripitaka, pick_int(envolop)),
                        sutra_name=envolop.split('-')[-1],
                        reel_no=0)

            content_pages = []
            volumes = sorted(os.listdir(path.join(root, envolop)))
            for volume in volumes:
                if not volume.startswith('.'):
                    v_row = get_volume_info(tripitaka, root, volume, envolop)
                    rows.append(v_row)
                    sutra['due_reel_count'] += 1
                    if '封面' not in volume and '封底' not in volume:
                        content_pages += v_row[5]

                    reel['reel_no'] += 1
                    reel['reel_code'] = '%s_%d' % (reel['sutra_code'], reel['reel_no'])
                    reel['start_volume'] = '_'.join(v_row[5][0].split('_')[:-1])
                    reel['end_volume'] = '_'.join(v_row[5][-1].split('_')[:-1])
                    reel['start_page'] = int(v_row[5][0].split('_')[-1])
                    reel['end_page'] = int(v_row[5][-1].split('_')[-1])
                    reel['remark'] = '-' in volume and volume.split('-')[-1] or ''
                    reels.append(dict(reel))

            sutra['start_volume'] = '_'.join(content_pages[0].split('_')[:-1])
            sutra['start_page'] = int(content_pages[0].split('_')[-1])
            sutra['end_volume'] = '_'.join(content_pages[-1].split('_')[:-1])
            sutra['end_page'] = int(content_pages[-1].split('_')[-1])
            sutra['existed_reel_count'] = sutra['due_reel_count']
            sutras.append(sutra)

    with open(path.join(root, 'Volume-%s.csv' % tripitaka), 'w', newline='') as fn:
        writer = csv.writer(fn)
        writer.writerow(fields)
        writer.writerows(rows)
    if level == 2 and gen_sutra:
        with open(path.join(root, 'Sutra-%s.csv' % tripitaka), 'w', newline='') as fn:
            fields = 'unified_sutra_code,sutra_code,sutra_name,due_reel_count,existed_reel_count,author,' \
                     'trans_time,start_volume,start_page,end_volume,end_page,remark'.split(',')
            writer = csv.writer(fn)
            writer.writerow(fields)
            writer.writerows([s.get(k, '') for k in fields] for s in sutras)

        with open(path.join(root, 'Reel-%s.csv' % tripitaka), 'w', newline='') as fn:
            fields = 'unified_sutra_code,sutra_code,sutra_name,reel_code,reel_no,start_volume,start_page,' \
                     'end_volume,end_page,remark'.split(',')
            writer = csv.writer(fn)
            writer.writerow(fields)
            writer.writerows([s.get(k, '') for k in fields] for s in reels)


def reorder_files(src_dir, dst_dir, prefix):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    orders = {}
    for fn in sorted(os.listdir(src_dir)):
        if fn.startswith('.'):
            continue
        src_file = os.path.join(src_dir, fn)
        if os.path.isdir(src_file):
            reorder_files(src_file, os.path.join(dst_dir, fn), '%s_%d' % (prefix, pick_int(fn)))
        else:
            page, suffix = fn.split('.', maxsplit=2)
            if page[0] not in 'fb':
                if page not in orders:
                    orders[page] = len(orders) + 1
                page = '%d' % orders[page]
            shutil.copy(src_file, os.path.join(dst_dir, '%s_%s.%s' % (prefix, page, suffix)))


if __name__ == '__main__':
    import fire

    fire.Fire(generate_volume_from_dir)
    print('finished!')
