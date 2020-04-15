#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from os import path
from bson.objectid import ObjectId
from tornado.escape import native_str
from elasticsearch.exceptions import ConnectionTimeout
from .tool.diff import Diff
from .base import PageHandler
from .tool.esearch import find_one, find_neighbor
from controller import errors as e
from controller import validate as v
from controller.base import BaseHandler


class PageBoxApi(PageHandler):
    URL = ['/api/page/box/@page_name']

    def post(self, page_name):
        """ 提交切分校对"""
        try:
            self.save_box(self, page_name)
        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_box(self, page_name):
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
        rules = [(v.not_empty, 'blocks', 'columns', 'chars')]
        self.validate(self.data, rules)
        update = self.get_box_update(self.data, page)
        self.db.page.update_one({'_id': page['_id']}, {'$set': update})
        valid, message, box_type, out_boxes = self.check_box_cover(page)
        self.send_data_response(valid=valid, message=message, box_type=box_type, out_boxes=out_boxes)
        self.add_log('update_box', target_id=page['_id'], context=page['name'])


class PageOrderApi(PageHandler):
    URL = ['/api/page/order/@page_name']

    def post(self, page_name):
        """ 提交字序校对"""
        try:
            self.save_order(self, page_name)
        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_order(self, page_name):
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
        self.validate(self.data, [(v.not_empty, 'chars_col')])
        if not self.cmp_char_cid(page['chars'], self.data['chars_col']):
            return self.send_error_response(e.cid_not_identical, message='检测到字框有增减，请刷新页面')
        if len(self.data['chars_col']) != len(page['columns']):
            return self.send_error_response(e.col_not_identical, message='提交的字序中列数有变化，请检查')
        chars = self.update_char_order(page['chars'], self.data['chars_col'])
        update = dict(chars=chars, chars_col=self.data['chars_col'])
        self.db.page.update_one({'_id': page['_id']}, {'$set': update})
        self.send_data_response()
        self.add_log('update_order', target_id=page['_id'], context=page['name'])


class PageCmpTxtApi(PageHandler):
    URL = '/api/page/cmp_txt/@page_name'

    def post(self, page_name):
        """ 根据OCR文本从CBETA库中查找相似文本作为比对本"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            ocr = self.get_txt(page, 'ocr')
            num = self.prop(self.data, 'num', 1)
            cmp, hit_page_codes = find_one(ocr, int(num))
            if cmp:
                self.send_data_response(dict(cmp=cmp, hit_page_codes=hit_page_codes))
            else:
                self.send_error_response(e.no_object, message='未找到比对文本')

        except self.DbError as error:
            return self.send_db_error(error)
        except ConnectionTimeout as error:
            return self.send_db_error(error)


class PageCmpTxtNeighborApi(PageHandler):
    URL = '/api/page/cmp_txt/neighbor'

    def post(self):
        """ 获取比对文本的前后页文本"""
        # param page_code: 当前cmp文本的page_code（对应于es库中的page_code）
        # param neighbor: prev/next，根据当前cmp文本的page_code往前或者往后找一条数据
        try:
            rules = [(v.not_empty, 'cmp_page_code', 'neighbor')]
            self.validate(self.data, rules)
            neighbor = find_neighbor(self.data.get('cmp_page_code'), self.data.get('neighbor'))
            if neighbor:
                txt = Diff.pre_cmp(''.join(neighbor['_source']['origin']))
                self.send_data_response(dict(txt=txt, code=neighbor['_source']['page_code']))
            else:
                self.send_data_response(dict(txt='', message='没有更多内容'))

        except self.DbError as error:
            return self.send_db_error(error)


class PageTxtDiffApi(PageHandler):
    URL = '/api/page/txt/diff'

    def post(self):
        """ 用户提交纯文本后重新比较，并设置修改痕迹"""
        try:
            rules = [(v.not_empty, 'texts')]
            self.validate(self.data, rules)
            diff_blocks = self.diff(*self.data['texts'])
            if self.data.get('hints'):
                diff_blocks = self.set_hints(diff_blocks, self.data['hints'])
            cmp_data = self.render_string('page_text_area.html', blocks=diff_blocks,
                                          sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))
            cmp_data = native_str(cmp_data)
            self.send_data_response(dict(cmp_data=cmp_data))

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def set_hints(diff_blocks, hints):
        for h in hints:
            line_segments = diff_blocks.get(h['block_no'], {}).get(h['line_no'])
            if not line_segments:
                continue
            for s in line_segments:
                if s['base'] == h['base'] and s['cmp1'] == h['cmp1']:
                    s['selected'] = True
        return diff_blocks


class DetectWideCharsApi(PageHandler):
    URL = '/api/page/txt/detect_chars'

    def post(self):
        """ 根据文本行内容识别宽字符"""
        try:
            mb4 = [[self.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)


class PageExportCharsApi(BaseHandler):
    URL = '/api/data/page/export_char'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_empty, 'page_names')]
            self.validate(self.data, rules)
            # 启动脚本，生成字表
            script = 'nohup python3 %s/gen_chars.py --page_names="%s" --username="%s" >> log/gen_chars.log 2>&1 &'
            os.system(script % (path.dirname(__file__), ','.join(self.data['page_names']), self.username))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class UpdatePageSourceApi(BaseHandler):
    URL = '/api/data/(page)/source'

    def post(self, collection):
        """ 批量更新分类"""
        try:
            rules = [(v.not_empty, 'source'), (v.not_both_empty, '_id', '_ids')]
            self.validate(self.data, rules)

            update = {'$set': {'source': self.data['source']}}
            if self.data.get('_id'):
                r = self.db[collection].update_one({'_id': ObjectId(self.data['_id'])}, update)
                self.add_log('update_' + collection, target_id=self.data['_id'])
            else:
                r = self.db[collection].update_many({'_id': {'$in': [ObjectId(i) for i in self.data['_ids']]}}, update)
                self.add_log('update_' + collection, target_id=self.data['_ids'])
            self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)
