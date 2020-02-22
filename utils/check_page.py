#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pymongo
from datetime import datetime
from controller.page.tool import PageTool
from controller.page.base import PageHandler


def check_box_cover(db_name='tripitaka', uri='localhost'):
    db = pymongo.MongoClient(uri)[db_name]
    cnt = 0
    names = []
    uncovered = dict(字框不在栏框内=[], 列框不在栏框内=[], 字框不在列框内=[])
    while cnt < 1000:
        cnt += 1
        condition = {'source': {'$regex': '1200'}, 'name': {'$nin': names}}
        fields = ['name', 'width', 'height', 'blocks', 'columns', 'chars']
        pages = list(db.page.find(condition, {k: 1 for k in fields}).limit(10))
        if not pages:
            break

        for p in pages:
            names.append(p['name'])
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), p['name']))
            # 检查是否有未覆盖的框
            valid, message, invalid_ids = PageHandler.check_box_cover(p)
            if not valid:
                uncovered[message].append(p['name'])

    print('uncovered', uncovered)


def check_chars_col(db_name='tripitaka', uri='localhost'):
    def cmp_chars_col(chars_cols1, chars_cols2):
        if len(chars_cols1) != len(chars_cols2):
            return False
        for i, chars_col1 in enumerate(chars_cols1):
            for j, cid1 in enumerate(chars_col1):
                cid2 = chars_cols2[i][j] if len(chars_cols2[i]) > j else 0
                if cid1 != cid2:
                    return False
        return True

    db = pymongo.MongoClient(uri)[db_name]
    debug_name = ''
    cnt = 0
    handled = []
    invalid_order = []
    while cnt < 1000:
        cnt += 1
        project = {k: 1 for k in ['name', 'chars', 'blocks', 'columns']}
        condition = {'source': {'$regex': '1200'}, 'name': {'$nin': handled}}
        if debug_name:
            condition = {'name': debug_name}
        pages = list(db.page.find(condition, project).limit(10))
        if not pages:
            break
        for p in pages:
            handled.append(p['name'])
            print('[%s] processing %s' % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), p['name']))
            # 检查字序是否有问题
            old_chars_col = PageTool.get_chars_col(p['chars'])
            blocks, columns, chars = PageTool.reorder_boxes(page=p)
            new_chars_col = PageTool.get_chars_col(chars)
            if not cmp_chars_col(old_chars_col, new_chars_col):
                invalid_order.append(p['name'])
                # print('invalid:', p['name'])
        if debug_name:
            break

    print(invalid_order)


if __name__ == '__main__':
    import fire

    fire.Fire(check_chars_col)
    print('finished!')
