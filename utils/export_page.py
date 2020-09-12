#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json
import pymongo
from glob import glob
from bson import json_util
from wand.image import Image as wImage
from wand.color import Color
from wand.drawing import Drawing
from PIL import Image as Image, ImageDraw
from os import path, makedirs

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller.base import prop
from controller.page.base import PageHandler as Ph


def export_page(db_name='tripitaka', uri='localhost', out_dir=None, source='', phonetic=False, text_finished=False):
    conn = pymongo.MongoClient(uri)
    db = conn[db_name]
    cond = {'source': {'$regex': str(source)}} if source else {}
    if phonetic:
        cond['$or'] = [{f: {'$regex': '音釋|音释'}} for f in ['ocr', 'ocr_col', 'text']]
    out_dir = out_dir and str(out_dir) or source or 'pages'
    for index in range(1000):
        rows = list(db.page.find(cond).skip(index * 100).limit(100))
        if rows:
            if not path.exists(out_dir):
                makedirs(out_dir)
            print('export %d pages...' % len(rows))
            for p in rows:
                tasks = db.task.find({'doc_id': p['name'], 'task_type': {'$regex': '^text'}, 'status': 'finished'})
                if text_finished and not tasks:
                    continue
                for task in tasks:
                    p[task['task_type']] = Ph.html2txt(prop(task, 'result.txt_html', ''))

                p['_id'] = str(p['_id'])
                if p.get('create_time'):
                    p['create_time'] = p['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                with open(path.join(out_dir, '%s.json' % str(p['name'])), 'w') as f:
                    for k, v in list(p.items()):
                        if not v or k in ['lock', 'level', 'tasks']:
                            p.pop(k)
                    f.write(json_util.dumps(p, ensure_ascii=False))


# python3 ~/export_page.py --out_dir=1200 --source=1200 --phonetic=1 --text_finished=1 --db_name=... --uri=mongodb://...
def export_phonetic(json_dir):
    with open('phonetic.txt', 'w') as f:
        for json_file in sorted(glob(path.join(json_dir, '*.json'))):
            page = json.load(open(json_file))
            texts, tags = set(), []
            for i, field in enumerate(['text_proof_1', 'text_proof_2', 'text', 'ocr', 'ocr_col']):
                text = re.search(r'(音释|音釋)\|+(.+)$', page.get(field, ''))
                if text:
                    if texts and i > 1:
                        continue
                    text = text.group(2)
                    txt2 = re.sub('[YM]', '', text)
                    if txt2 not in texts:
                        texts.add(txt2)
                        tags.append((field, text))
            names = dict(text_proof_1='一校', text_proof_2='二校', text='旧审', ocr='字框', ocr_col='行文')
            for field, text in tags:
                f.write('%s(%s)\t%s\n' % (page['name'], names[field], text))


def export_label_data(db):
    fields = ['name', 'width', 'height', 'layout', 'blocks', 'columns', 'chars']
    pages = list(db.page.find({'remark_box': '10000张切分标注'}, {k: 1 for k in fields}))
    layout2nums = {'上下一栏': (2, 2), '上下两栏': (2, 3), '上下三栏': (2, 4), '左右两栏': (2, 2)}
    for p in pages:
        print('processing %s' % p['name'])
        p.pop('_id', 0)
        layout = p.pop('layout', 0)
        if layout and layout2nums.get(layout):
            p['v_num'], p['h_num'] = layout2nums.get(layout)
        blocks, columns, chars = p.get('blocks'), p.get('columns'), p.get('chars')
        for i, b in enumerate(blocks):
            keys = ['x', 'y', 'w', 'h', 'block_no']
            blocks[i] = {k: b.get(k) for k in keys}
        for i, b in enumerate(columns):
            keys = ['x', 'y', 'w', 'h', 'block_no', 'column_no']
            columns[i] = {k: b.get(k) for k in keys}
        for i, b in enumerate(chars):
            keys = ['x', 'y', 'w', 'h', 'block_no', 'column_no', 'char_no']
            chars[i] = {k: b.get(k) for k in keys}
        with open(path.join('/home/smjs/xiandu/10000-json', '%s.json' % p['name']), 'w') as fn:
            json.dump(p, fn)


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
        print('processing %s' % name)
        files = glob(path.join(big_dir, *name.split('_')[:-1], '%s.*' % name))
        if not files:
            print('can not find %s' % name)

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
            im.save(path.join(dst_dir, '%s.jpg' % name))
        except Exception as e:
            print('[%s] %s' % (e.__class__.__name__, str(e)))
            invalid.append(name)
    if invalid:
        print('%s invalid pages.\n%s' % (len(invalid), invalid))


def main(db_name='tripitaka', uri='localhost', func='export_box_by_pillow', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
    print('finished!')
