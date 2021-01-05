#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json
import math
import pymongo
from glob import glob
from bson import json_util
from os import path, makedirs
from wand.image import Image as wImage
from wand.color import Color
from wand.drawing import Drawing
from PIL import Image as Image, ImageDraw

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph


def export_page_txt(db, source='', dst_dir='', txt_field='adapt'):
    size = 10000
    cond = {'source': source}
    total_cnt = db.page.count_documents(cond)
    print('[%s]%s pages to process' % (hp.get_date_time(), total_cnt))
    page_nums = math.ceil(total_cnt / size)
    for i in range(page_nums):
        pages = list(db.page.find(cond, {'name': 1, 'chars': 1}).sort('_id', 1).skip(i * size).limit(size))
        for page in pages:
            print('[%s]processing %s' % (hp.get_date_time(), page['name']))
            txt = Ph.get_char_txt(page, txt_field)
            with open(path.join(dst_dir, '%s.txt' % page['name']), 'w') as wf:
                wf.writelines(txt.replace('|', '\n'))


def export_box_by_wand(db):
    big_dir = '/data/T/big'
    dst_dir = '/data/T/标注数据/10000张切分标注/vis'
    cond = {'remark_box': '10000张切分标注'}
    invalid = []
    fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
    pages = list(db.page.find(cond, {k: 1 for k in fields}))
    for page in pages:
        name = page['name']
        print('processing %s' % name)
        files = glob(path.join(big_dir, *name.split('_')[:-1], '%s.*' % name))
        if not files:
            print('can not find %s' % name)
        try:
            with wImage(filename=files[0]) as im:
                r = im.width / page['width']
                with Drawing() as draw:
                    draw.stroke_color = Color('blue')
                    draw.fill_color = Color('none')
                    draw.stroke_width = 1
                    for b in page['blocks']:
                        draw.rectangle(b['x'] * r, b['y'] * r, width=b['w'] * r, height=b['h'] * r)
                        draw(im)
                    draw.stroke_color = Color('green')
                    for c in page['columns']:
                        draw.rectangle(c['x'] * r, c['y'] * r, width=c['w'] * r, height=c['h'] * r)
                        draw(im)
                    draw.stroke_color = Color('red')
                    for c in page['chars']:
                        draw.rectangle(c['x'] * r, c['y'] * r, width=c['w'] * r, height=c['h'] * r)
                        draw(im)
                    dst_file = path.join(dst_dir, '%s.jpg' % name)
                    im.transform(resize='1200x')
                    im.compression_quality = 75
                    im.save(filename=dst_file)
        except Exception as e:
            print('[%s] %s' % (e.__class__.__name__, str(e)))
            invalid.append(name)

    print('%s invalid pages.\n%s' % (len(invalid), invalid))


def export_box_by_pillow(db):
    big_dir = '/data/T/big'
    dst_dir = '/data/T/标注数据/10000张切分标注/vis'
    cond = {'remark_box': '10000张切分标注'}
    invalid = []
    fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
    pages = list(db.page.find(cond, {k: 1 for k in fields}))
    for page in pages:
        name = page['name']
        files = glob(path.join(big_dir, *name.split('_')[:-1], '%s.*' % name))
        if not files:
            print('[%s]can not find image file' % name)
            continue
        vis_fn = path.join(dst_dir, '%s.jpg' % name)
        if path.exists(vis_fn):
            print('[%s]image file existed' % name)
            continue

        try:
            im = Image.open(files[0]).convert('RGB')
            w, h = im.size
            r = w / page['width']
            draw = ImageDraw.Draw(im)
            for b in page['blocks']:
                draw.rectangle(((b['x'] * r, b['y'] * r), ((b['x'] + b['w']) * r, (b['y'] + b['h']) * r)),
                               outline="#0000FF")
            for b in page['columns']:
                draw.rectangle(((b['x'] * r, b['y'] * r), ((b['x'] + b['w']) * r, (b['y'] + b['h']) * r)),
                               outline="#008800")
            for b in page['chars']:
                draw.rectangle(((b['x'] * r, b['y'] * r), ((b['x'] + b['w']) * r, (b['y'] + b['h']) * r)),
                               outline="#FF0000")
            im = im.resize((1200, int(1200 * h / w)), Image.ANTIALIAS)
            im.save(vis_fn)
        except Exception as e:
            print('[%s] %s' % (e.__class__.__name__, str(e)))
            invalid.append(name)
    if invalid:
        print('%s invalid pages.\n%s' % (len(invalid), invalid))


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished!')
