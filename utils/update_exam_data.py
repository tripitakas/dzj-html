#!/usr/bin/env python
# -*- coding: utf-8 -*-
# python3 utils/update_page.py --uri=uri --func=init_variants
# 更新考核和体验相关的数据和任务

import re
import sys
import math
import json
import random
import pymongo
from os import path

BASE_DIR = path.dirname(path.dirname(__file__))
sys.path.append(BASE_DIR)

from controller import helper as hp
from controller.page.base import PageHandler as Ph

names0 = ['GL_1434_5_10', 'GL_129_1_11', 'JX_260_1_249', 'JX_260_1_17', 'YB_29_283', 'QL_11_112', 'YB_24_400',
          'YB_25_108', 'QL_7_401', 'QL_11_375']
names1 = ['GL_1054_1_4', 'GL_78_9_18', 'JX_260_1_98', 'JX_260_1_239', 'YB_33_629', 'QL_26_175', 'YB_26_512',
          'YB_27_906', 'QL_24_691', 'QL_10_446']
names2 = ['GL_9_1_12', 'GL_1260_9_5', 'JX_260_1_103', 'JX_260_1_270', 'YB_25_931', 'QL_2_354', 'YB_32_967',
          'YB_22_995', 'QL_13_413', 'QL_4_629']
names3 = ['GL_1260_1_3', 'GL_922_2_21', 'JX_260_1_135', 'JX_260_1_194', 'YB_28_965', 'QL_10_413', 'YB_28_423',
          'YB_27_377', 'QL_24_17', 'QL_11_145']
names4 = ['GL_82_1_5', 'GL_1056_1_20', 'JX_260_1_280', 'JX_260_1_181', 'YB_28_867', 'QL_14_17', 'YB_28_171',
          'YB_29_769', 'QL_25_416', 'QL_1_210']
names5 = ['GL_1056_2_21', 'GL_62_1_37', 'JX_260_1_148', 'JX_245_3_100', 'YB_29_813', 'QL_10_715', 'YB_26_41',
          'YB_30_159', 'QL_25_48', 'QL_10_571']
names6 = ['GL_165_1_28', 'GL_922_1_21', 'JX_260_1_83', 'JX_260_2_12', 'YB_28_797', 'QL_12_176', 'YB_26_172',
          'YB_23_132', 'QL_13_481', 'QL_7_385']
names7 = ['GL_923_2_16', 'GL_1054_4_2', 'JX_260_1_175', 'JX_260_1_91', 'YB_34_151', 'QL_7_337', 'YB_31_636',
          'YB_31_692', 'QL_1_309', 'QL_9_496']
names8 = ['GL_165_1_12', 'GL_914_1_20', 'JX_260_1_64', 'JX_260_1_210', 'YB_24_228', 'QL_10_160', 'YB_33_418',
          'YB_25_562', 'QL_25_400', 'QL_9_513']
names9 = ['GL_1051_7_23', 'GL_9_1_16', 'JX_260_2_23', 'JX_245_3_142', 'YB_24_667', 'QL_24_71', 'YB_33_748',
          'YB_27_257', 'QL_26_391', 'QL_2_772']


def get_exam_names():
    names = []
    for i in range(10):
        names.extend(eval('names%s' % i))
    return names


def transform_box(box, mode='reduce,move'):
    if 'enlarge' in mode:
        box['w'] = round(box['w'] * 1.1, 1)
        box['h'] = round(box['h'] * 1.1, 1)
    if 'reduce' in mode:
        box['w'] = round(box['w'] * 0.8, 1)
        box['h'] = round(box['h'] * 0.8, 1)
    if 'move' in mode:
        box['x'] = box['x'] + int(box['w'] * 0.1)
        box['y'] = box['y'] + int(box['h'] * 0.1)


def add_random_column(boxes):
    random_box = boxes[random.randint(0, len(boxes) - 1)].copy()
    transform_box(random_box)
    max_cid = max([int(c.get('cid') or 0) for c in boxes])
    random_box['cid'] = max_cid + 1
    last = boxes[-1]
    random_box['column_id'] = 'b%sc%s' % (last['block_no'], last['column_no'] + 1)
    boxes.append(random_box)


def initial_bak_data(db):
    """ 设置备份数据"""
    pages = db.page.find({})
    for p in pages:
        if not p.get('bak'):
            bak = {k: p.get(k) for k in ['blocks', 'columns', 'chars'] if p.get(k)}
            db.page.update_one({'_id': p['_id']}, {'$set': {'bak': bak}})


def reset_bak_data(db, names=None, data_type=None):
    """ 恢复数据"""
    condition = {}
    if names:
        condition = {'name': {'$in': names}}
    elif data_type == 'exam':
        condition = {'name': {'$in': get_exam_names()}}
    elif data_type == 'experience':
        condition = {'name': {'$regex': 'EX'}}
    pages = db.page.find(condition)
    for p in pages:
        if p.get('bak'):
            db.page.update_one({'_id': p['_id']}, {'$set': p['bak']})


def shuffle_exam_data(db, names=None):
    """ 处理考试数据：栏框进行放大或缩小，列框进行缩放和增删，字框进行缩放和增删"""
    names = names or get_exam_names()
    names = names.split(',') if isinstance(names, str) else names
    for i, name in enumerate(names):
        p = db.page.find_one({'name': name})
        print('processing %s' % name if p else '%s not existed' % name)
        assert len(p['chars']) > 10
        assert len(p['columns']) > 2
        mode = 'enlarge,move' if i % 2 else 'reduce,move'
        transform_box(p['blocks'][0], mode)
        transform_box(p['columns'][0], mode)
        transform_box(p['columns'][random.randint(0, len(p['columns']) - 1)], mode)
        add_random_column(p['columns'])
        transform_box(p['chars'][-1], mode)
        transform_box(p['chars'][random.randint(0, len(p['chars']) - 1)], mode)
        p['chars'].pop(random.randint(0, len(p['chars']) - 1))
        p['chars'].pop(random.randint(0, len(p['chars']) - 1))
        db.page.update_one({'_id': p['_id']}, {'$set': {k: p.get(k) for k in ['blocks', 'columns', 'chars']}})


def add_users(db):
    """ 创建考核以及练习账号"""
    users = []
    for i in range(10):
        users.append({
            'name': '考核账号%d' % (i + 1),
            'email': 'exam%d@tripitakas.net' % (i + 1),
            'roles': "切分校对员,文字校对员,聚类校对员",
            'password': hp.gen_id('123abc'),
        })
    users.append({
        'name': '练习账号',
        'email': 'practice@tripitakas.net',
        'roles': "切分校对员,文字校对员,聚类校对员",
        'password': hp.gen_id('123abc'),
    })
    db.user.insert_many(users)


def publish_tasks_and_assign(db):
    """ 发布并指派任务"""

    def get_task(page_name, tsk_type, num=None, params=None, r_user=None):
        steps = Ph.prop(Ph.task_types, '%s.steps' % task_type)
        if steps:
            steps = {'todo': [s[0] for s in steps]}
        return dict(task_type=tsk_type, num=int(num or 1), batch='考核任务',
                    collection='page', id_name='name', doc_id=page_name, status='picked',
                    steps=steps, priority=2, pre_tasks=None, params=params, result={},
                    create_time=Ph.now(), updated_time=Ph.now(), publish_time=Ph.now(),
                    publish_user_id=None, publish_by='管理员',
                    picked_user_id=r_user['_id'], picked_by=r_user['name'],
                    picked_time=Ph.now())

    tasks = []
    task_type = 'cut_proof'
    # 创建考核任务并指派任务
    for i in range(10):
        print('processing user %s' % (i + 1))
        user = db.user.find_one({'email': 'exam%d@tripitakas.net' % (i + 1)})
        for name in eval('names%s' % i):
            tasks.append(get_task(name, task_type, r_user=user))
    # 创建体验任务并指派任务
    user = db.user.find_one({'email': 'practice@tripitakas.net'})
    pages = list(db.page.find({'name': {'$regex': 'EX'}}, {'name': 1}))
    for p in pages:
        tasks.append(get_task(p['name'], task_type, r_user=user))

    db.task.insert_many(tasks)


def reset_exam_data_and_tasks(db, user_no=None):
    """ 重置考核任务状态"""
    # 重置任务
    cond = dict(batch='考核任务')
    if user_no:
        cond['picked_by'] = '考核账号%d' % user_no
    db.task.update_many(cond, {'$set': {'status': 'picked'}})
    db.task.update_many(cond, {'$unset': {
        'finished_time': '', 'steps.submitted': '', 'result.steps_finished': ''
    }})
    # 重置数据
    names = eval('names%s' % (user_no - 1)) if user_no else get_exam_names()
    db.page.update_many({'name': {'$in': names}}, {'$unset': {'tasks': ''}})


def initial_run(db):
    """ 初始化"""
    initial_bak_data(db)
    shuffle_exam_data(db)
    add_users(db)
    publish_tasks_and_assign(db)


def reset_user_data_and_tasks(db, user_no=None):
    """ 重置体验数据、考核数据以及考核任务"""
    assert not user_no or user_no in range(1, 11)
    names = eval('names%s' % (user_no - 1)) if user_no else None
    reset_bak_data(db, names=names, data_type='exam')
    shuffle_exam_data(db, names)
    reset_exam_data_and_tasks(db, user_no)


def main(db_name='tripitaka', uri='localhost', func='', **kwargs):
    db = pymongo.MongoClient(uri)[db_name]
    eval(func)(db, **kwargs)


if __name__ == '__main__':
    import fire

    fire.Fire(main)
