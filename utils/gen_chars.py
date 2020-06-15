#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 将page['chars']中的数据同步到char表，包括增删改等
# 数据同步时，检查字框的char_id字序信息和x/y/w/h等位置信息，如果发生了改变，则进行同步
# python3 utils/extract_img.py --condition= --user_name=

import sys
import json
import math
import pymongo
from os import path
from datetime import datetime

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.base import BaseHandler as Bh


def gen_chars(db=None, db_name='tripitaka', uri=None, reset=False,
              condition=None, page_names=None, username=None):
    """ 从页数据中导出字数据"""

    def is_changed(a, b):
        """ 检查坐标和字序是否发生变化"""
        if a['char_id'] != b['char_id']:
            return True
        for k in ['x', 'y', 'w', 'h']:
            if a['pos'][k] != b['pos'][k]:
                return True
        for k in ['x', 'y', 'w', 'h', 'cid']:
            if not a.get('column') or not b.get('column'):
                return True
            if a['column'][k] != b['column'][k]:
                return True
        return False

    db = db or uri and pymongo.MongoClient(uri)[db_name] or hp.connect_db(hp.load_config()['database'])[0]
    if reset:
        db.char.delete_many({})

    if page_names:
        page_names = page_names.split(',') if isinstance(page_names, str) else page_names
        condition = {'name': {'$in': page_names}}
    elif isinstance(condition, str):
        condition = json.loads(condition)
    elif not condition:
        condition = {}

    names = ['YB_24_259', 'YB_24_262', 'YB_24_264', 'YB_24_267', 'YB_24_269', 'YB_24_271', 'YB_24_273', 'YB_24_400', 'YB_24_47', 'YB_24_522', 'YB_24_579', 'YB_24_663', 'YB_24_665', 'YB_24_667', 'YB_24_807', 'YB_24_813', 'YB_24_862', 'YB_24_910', 'YB_25_106', 'YB_25_108', 'YB_25_207', 'YB_25_23', 'YB_25_319', 'YB_25_334', 'YB_25_371', 'YB_25_375', 'YB_25_377', 'YB_25_474', 'YB_25_520', 'YB_25_562', 'YB_25_600', 'YB_25_692', 'YB_25_840', 'YB_25_856', 'YB_25_858', 'YB_25_897', 'YB_25_931', 'YB_26_172', 'YB_26_203', 'YB_26_263', 'YB_26_333', 'YB_26_337', 'YB_26_41', 'YB_26_463', 'YB_26_512', 'YB_26_559', 'YB_26_607', 'YB_26_638', 'YB_26_745', 'YB_26_780', 'YB_26_783', 'YB_26_797', 'YB_26_834', 'YB_26_862', 'YB_26_864', 'YB_26_866', 'YB_26_870', 'YB_26_874', 'YB_26_890', 'YB_26_898', 'YB_26_929', 'YB_26_959', 'YB_27_107', 'YB_27_191', 'YB_27_257', 'YB_27_377', 'YB_27_45', 'YB_27_480', 'YB_27_531', 'YB_27_54', 'YB_27_563', 'YB_27_594', 'YB_27_613', 'YB_27_625', 'YB_27_633', 'YB_27_638', 'YB_27_654', 'YB_27_659', 'YB_27_673', 'YB_27_68', 'YB_27_75', 'YB_27_772', 'YB_27_822', 'YB_27_906', 'YB_27_978', 'YB_28_171', 'YB_28_250', 'YB_28_295', 'YB_28_370', 'YB_28_423', 'YB_28_455', 'YB_28_476', 'YB_28_492', 'YB_28_500', 'YB_28_515', 'YB_28_524', 'YB_28_529', 'YB_28_557', 'YB_28_594', 'YB_28_600', 'YB_28_604', 'YB_28_608', 'YB_28_611', 'YB_28_615', 'YB_28_619', 'YB_28_624', 'YB_28_645', 'YB_28_649', 'YB_28_652', 'YB_28_656', 'YB_28_670', 'YB_28_679', 'YB_28_683', 'YB_28_689', 'YB_28_696', 'YB_28_704', 'YB_28_712', 'YB_28_736', 'YB_28_740', 'YB_28_749', 'YB_28_751', 'YB_28_760', 'YB_28_77', 'YB_28_772', 'YB_28_775', 'YB_28_779', 'YB_28_781', 'YB_28_79', 'YB_28_793', 'YB_28_795', 'YB_28_797', 'YB_28_799', 'YB_28_809', 'YB_28_812', 'YB_28_821', 'YB_28_83', 'YB_28_852', 'YB_28_861', 'YB_28_867', 'YB_28_88', 'YB_28_885', 'YB_28_890', 'YB_28_899', 'YB_28_907', 'YB_28_914', 'YB_28_918', 'YB_28_920', 'YB_28_928', 'YB_28_935', 'YB_28_951', 'YB_28_965', 'YB_28_98', 'YB_29_104', 'YB_29_108', 'YB_29_112', 'YB_29_120', 'YB_29_124', 'YB_29_130', 'YB_29_140', 'YB_29_185', 'YB_29_193', 'YB_29_20', 'YB_29_210', 'YB_29_221', 'YB_29_225', 'YB_29_234', 'YB_29_245', 'YB_29_257', 'YB_29_264', 'YB_29_269', 'YB_29_277', 'YB_29_283', 'YB_29_297', 'YB_29_30', 'YB_29_307', 'YB_29_312', 'YB_29_32', 'YB_29_328', 'YB_29_341', 'YB_29_347', 'YB_29_361', 'YB_29_372', 'YB_29_379', 'YB_29_386', 'YB_29_398', 'YB_29_403', 'YB_29_407', 'YB_29_413', 'YB_29_599', 'YB_29_677', 'YB_29_769', 'YB_29_813', 'YB_29_861', 'YB_29_953', 'YB_30_159', 'YB_30_207', 'YB_30_362', 'YB_30_413', 'YB_30_454', 'YB_30_507', 'YB_30_577', 'YB_30_623', 'YB_30_708', 'YB_30_774', 'YB_30_80', 'YB_30_894', 'YB_31_24', 'YB_31_297', 'YB_31_312', 'YB_31_354', 'YB_31_422', 'YB_31_459', 'YB_31_584', 'YB_31_636', 'YB_31_638', 'YB_31_642', 'YB_31_644', 'YB_31_663', 'YB_31_692', 'YB_31_730', 'YB_31_859', 'YB_31_914', 'YB_32_117', 'YB_32_194', 'YB_32_27', 'YB_32_346', 'YB_32_391', 'YB_32_438', 'YB_32_503', 'YB_32_613', 'YB_32_671', 'YB_32_698', 'YB_32_772', 'YB_32_860', 'YB_32_967', 'YB_33_156', 'YB_33_220', 'YB_33_308', 'YB_33_362', 'YB_33_418', 'YB_33_525', 'YB_33_629', 'YB_33_724', 'YB_33_748', 'YB_33_776', 'YB_33_858', 'YB_33_955', 'YB_33_967', 'YB_34_151', 'YB_34_216']
    once_size = 300
    condition = {'name': {'$in': names}}
    total_count = db.page.count_documents(condition)
    log_id = Bh.add_op_log(db, 'gen_chars', 'ongoing', [], username)
    fields1 = ['name', 'source', 'columns', 'chars']
    fields2 = ['source', 'cid', 'char_id', 'txt', 'nor_txt', 'ocr_txt', 'ocr_col', 'cmp_txt', 'alternatives']
    for i in range(int(math.ceil(total_count / once_size))):
        pages = list(db.page.find(condition, {k: 1 for k in fields1}).skip(i * once_size).limit(once_size))
        p_names = [p['name'] for p in pages]
        print('[%s]processing %s' % (hp.get_date_time(), ','.join(p_names)))
        # 查找、分类chars
        chars, char_names, invalid_chars, invalid_pages, valid_pages = [], [], [], [], []
        for p in pages:
            try:
                id2col = {col['column_id']: {k: col[k] for k in ['cid', 'x', 'y', 'w', 'h']} for col in p['columns']}
                for c in p['chars']:
                    try:
                        char_names.append('%s_%s' % (p['name'], c['cid']))
                        m = dict(page_name=p['name'], txt_level=0, img_need_updated=True)
                        m['name'] = '%s_%s' % (p['name'], c['cid'])
                        m.update({k: c[k] for k in fields2 if c.get(k)})
                        m.update({k: int(c[k] * 1000) for k in ['cc', 'sc'] if c.get(k)})
                        m['ocr_txt'] = c.get('alternatives', '')[:1] or c.get('ocr_col') or ''
                        m['txt'] = c.get('txt') or m['ocr_txt']
                        m['pos'] = dict(x=c['x'], y=c['y'], w=c['w'], h=c['h'])
                        m['column'] = id2col.get('b%sc%s' % (c['block_no'], c['column_no']))
                        m['uid'] = hp.align_code('%s_%s' % (p['name'], c['char_id'][1:].replace('c', '_')))
                        chars.append(m)
                    except KeyError as e:
                        print(e)
                        invalid_chars.append('%s_%s' % (p['name'], c['cid']))
                valid_pages.append(p['name'])
            except KeyError:
                invalid_pages.append(p['name'])

        # 删除多余的chars
        deleted = list(db.char.find({'page_name': {'$in': p_names}, 'name': {'$nin': char_names}}, {'name': 1}))
        if deleted:
            db.char.delete_many({'_id': {'$in': [d['_id'] for d in deleted]}})
            print('delete %s records: %s' % (len(deleted), ','.join([c['name'] for c in deleted])))
        # 更新已存在的chars。检查和更新char_id、uid、pos三个字段
        chars_dict = {c['name']: c for c in chars}
        existed = list(db.char.find({'name': {'$in': [c['name'] for c in chars]}}))
        if existed:
            changed = []
            for e in existed:
                c = chars_dict.get(e['name'])
                if is_changed(e, c):
                    changed.append(c['name'])
                    update = {k: c[k] for k in ['char_id', 'uid', 'pos', 'column'] if c.get(k)}
                    db.char.update_one({'_id': e['_id']}, {'$set': {**update, 'img_need_updated': True}})
            if changed:
                print('update changed %s records: %s' % (len(changed), ','.join([c for c in changed])))
        # 插入不存在的chars
        existed_id = [c['name'] for c in existed]
        un_existed = [c for c in chars if c['name'] not in existed_id]
        if un_existed:
            db.char.insert_many(un_existed, ordered=False)
            print('insert new %s records: %s' % (len(un_existed), ','.join([c['name'] for c in un_existed])))
        log = dict(inserted_char=[c['name'] for c in un_existed], updated_char=[c['name'] for c in existed],
                   deleted_char=[c['name'] for c in deleted], invalid_char=invalid_chars,
                   valid_pages=valid_pages, invalid_pages=invalid_pages,
                   create_time=datetime.now())
        db.oplog.update_one({'_id': log_id}, {'$addToSet': {'content': log}})
    db.oplog.update_one({'_id': log_id}, {'$set': {'status': 'finished'}})


if __name__ == '__main__':
    import fire

    fire.Fire(gen_chars)
