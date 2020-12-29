#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import os
import json
import math
import random
import logging
from bson.objectid import ObjectId
from tornado.escape import native_str, url_escape, to_basestring
from .page import Page
from .tool.diff import Diff
from .base import PageHandler
from controller import errors as e
from controller import helper as h
from controller import validate as v
from controller.base import BaseHandler
from controller.char.base import CharHandler
from .tool.esearch import find_one, find_neighbor
from utils.gen_chars import gen_chars
from utils.extract_img import extract_img


class PageUploadApi(BaseHandler):
    URL = '/api/data/page/upload'

    def post(self):
        """ 批量上传，供小欧调用"""
        try:
            source = self.data.get('source')
            layout = self.data.get('layout')
            upload_file = self.request.files.get('json')
            page_names = json.loads(to_basestring(upload_file[0]['body']))
            page_names = [name.rsplit('.', 1)[0] for name in page_names]
            logging.info('upload page start, %s pages total' % len(page_names))

            existed, size = [], 10000
            count = math.ceil(len(page_names) / size)
            for i in range(count):
                pages = list(self.db.page.find({'name': {'$in': page_names[i * size: (i + 1) * size]}}, {'name': 1}))
                existed.extend([p['name'] for p in pages])

            if existed:
                logging.info('upload page, find %s pages existed' % len(existed))
                page_names = list(set(page_names) - set(existed))
                # page_names = [name for name in page_names if name not in existed]
            if page_names:
                logging.info('upload page, %s valid pages to insert' % len(page_names))
                pages = [dict(name=n, source=source, layout=layout) for n in page_names]
                self.db.page.insert_many(pages, ordered=False)

            self.add_log('upload_page', content='%s pages, %s' % (len(page_names or []), page_names or ''))
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageUpsertApi(PageHandler):
    URL = '/api/page'

    def post(self):
        """ 新增或修改"""
        try:
            r = Page.save_one(self.db, 'page', self.data)
            if r.get('status') == 'success':
                self.add_log('%s_page' % ('update' if r.get('update') else 'add'), content=r.get('message'))
                self.send_data_response(r)
            else:
                self.send_error_response(r.get('errors'))

        except self.DbError as error:
            return self.send_db_error(error)


class PageSourceApi(BaseHandler):
    URL = '/api/page/source'

    def post(self):
        """ 更新分类"""
        try:
            if not self.data.get('source'):
                return self.send_error_response(e.not_allowed_empty, message='分类不许为空')

            if self.data.get('page_names'):
                page_names = self.data['page_names']
                page_names = page_names.split(',') if isinstance(page_names, str) else page_names
                r = self.db.page.update_many({'name': {'$in': page_names}}, {'$set': {'source': self.data['source']}})
                return self.send_data_response(dict(count=r.matched_count))

            if self.data.get('search'):
                condition = Page.get_page_search_condition(self.data['search'])[0]
                r = self.db.page.update_many(condition, {'$set': {'source': self.data['source']}})
                return self.send_data_response(dict(matched_count=r.matched_count))

            if self.request.files.get('names_file'):
                names_file = self.request.files.get('names_file')
                names_str = str(names_file[0]['body'], encoding='utf-8')
                try:
                    page_names = json.loads(names_str)
                except json.decoder.JSONDecodeError:
                    ids_str = re.sub(r'(\n|\r\n)+', ',', names_str)
                    page_names = ids_str.split(r',')
                page_names = [n for n in page_names if n]
                r = self.db.page.update_many({'name': {'$in': page_names}}, {'$set': {'source': self.data['source']}})
                return self.send_data_response(dict(matched_count=r.matched_count))

        except self.DbError as error:
            return self.send_db_error(error)


class PageDeleteApi(BaseHandler):
    URL = '/api/page/delete'

    def post(self):
        """ 批量删除"""
        try:
            rules = [(v.not_both_empty, 'page_name', 'page_names')]
            self.validate(self.data, rules)

            page_names = self.data.get('page_names') or [self.data['page_name']]
            tasks = list(self.db.task.find({'doc_id': {'$in': page_names}}, {'doc_id': 1}))
            task_names = {t['doc_id'] for t in tasks}
            page_names = [name for name in page_names if name not in task_names]
            deleted_count = 0
            if page_names:
                r = self.db.page.delete_many({'name': {'$in': page_names}})
                self.add_log('delete_page', target_name=page_names)
                deleted_count = r.deleted_count
            self.send_data_response(dict(deleted_count=deleted_count, existed_count=len(task_names)))

        except self.DbError as error:
            return self.send_db_error(error)


class PageBoxApi(PageHandler):
    URL = ['/api/page/box/@page_name']

    def post(self, page_name):
        """ 提交切分校对。切分数据以page表为准，box_level/box_logs等记录在page['chars']中，坐标信息同步更新char表"""
        try:
            self.save_box(self, page_name)
            return self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_box(self, page_name, task_type=None):
        """ 保存用户提交。包括框修改、框序和用户序线"""
        page = self.db.page.find_one({'name': page_name})
        if not page:
            self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

        rules = [(v.not_empty, 'op')]
        self.validate(self.data, rules)
        page_updated = self.get_user_submit(self.data, page, task_type)
        self.db.page.update_one({'_id': page['_id']}, {'$set': page_updated})
        self.add_log('update_box', target_id=page['_id'], target_name=page['name'])
        if page.get('has_gen_chars'):  # 更新char表和字图
            gen_chars(db=self.db, page_names=page_name, username=self.username)
            script = 'nohup python3 %s/utils/extract_img.py --username=%s --regen=%s >> log/extract_img_%s.log 2>&1 &'
            script = script % (h.BASE_DIR, self.username, 1, h.get_date_time(fmt='%Y%m%d%H%M%S'))
            os.system(script)

        return page


class PageBlocksApi(PageHandler):
    URL = ['/api/page/block/@page_name']

    def post(self, page_name):
        """ 提交栏框校对"""
        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)

            rules = [(v.not_empty, 'blocks')]
            self.validate(self.data, rules)
            self.db.page.update_one({'_id': page['_id']}, {'$set': {'blocks': self.data['blocks']}})
            self.send_data_response({'valid': True})

        except self.DbError as error:
            return self.send_db_error(error)


class PageCharBoxApi(PageHandler):
    URL = '/api/page/char/box/@char_name'

    def post(self, char_name):
        """ 更新字符的box"""

        try:
            rules = [(v.not_empty, 'pos')]
            self.validate(self.data, rules)
            page_name, cid = '_'.join(char_name.split('_')[:-1]), int(char_name.split('_')[-1])
            page = self.db.page.find_one({'name': page_name, 'chars.cid': cid},
                                         {'name': 1, 'tasks': 1, 'chars.$': 1})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            # 检查数据等级和积分
            char = page['chars'][0]
            self.check_box_level_and_point(self, char, page, self.data.get('task_type'))
            if h.cmp_obj(char, self.data, ['pos']):
                return self.send_error_response(e.not_changed)
            # 检查、设置box_logs
            old_logs = char.get('box_logs') or [{'pos': {k: char.get(k) for k in ['x', 'y', 'w', 'h']}}]
            box_logs = self.merge_box_logs({'pos': self.data['pos']}, old_logs)
            # 更新page表和char表
            box_level = self.get_user_box_level(self, self.data.get('task_type'))
            update = {**self.data['pos'], 'box_logs': box_logs, 'box_level': box_level}
            r1 = self.db.page.update_one({'_id': page['_id'], 'chars.cid': cid}, {'$set': {
                'chars.$.' + k: update[k] for k in ['x', 'y', 'w', 'h', 'box_level', 'box_logs']
            }})
            r2 = self.db.char.update_one({'name': char_name}, {'$set': {
                'pos': self.data['pos'], 'img_need_updated': True
            }})
            self.add_log('update_box', None, char_name, update)
            ret = dict(box_logs=box_logs)
            if r1.modified_count and r2.modified_count:  # 立即生成字图
                char = self.db.char.find_one({'name': char_name})
                extract_img(db=self.db, username=self.username, regen=True, chars=[char])
                ret['img_url'] = self.get_web_img(char_name, 'char') + '?v=%d' % random.randint(0, 9999)
            self.send_data_response(ret)

        except self.DbError as error:
            return self.send_db_error(error)


class PageCharTxtApi(PageHandler):
    URL = '/api/page/char/txt/@char_name'

    def post(self, char_name):
        """ 更新字符的txt"""

        try:
            rules = [(v.not_none, 'txt', 'txt_type'), (v.is_txt, 'txt'), (v.is_txt_type, 'txt_type')]
            self.validate(self.data, rules)
            page_name, cid = '_'.join(char_name.split('_')[:-1]), int(char_name.split('_')[-1])
            cond = {'name': page_name, 'chars.cid': cid}
            page = self.db.page.find_one(cond, {'name': 1, 'tasks': 1, 'chars.$': 1})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            # 检查数据等级和积分
            char = page['chars'][0]
            CharHandler.check_txt_level_and_point(self, char, self.data.get('task_type'))
            # 检查参数，设置更新
            fields = ['txt', 'nor_txt', 'txt_type', 'remark']
            update = {k: self.data[k] for k in fields if self.data.get(k) not in ['', None]}
            if h.cmp_obj(update, char, fields):
                return self.send_error_response(e.not_changed)
            char.update(update)
            my_log = {k: self.data[k] for k in fields + ['task_type'] if self.data.get(k) not in ['', None]}
            char['txt_logs'] = self.merge_txt_logs(my_log, char.get('txt_logs'))
            char['txt_level'] = CharHandler.get_user_txt_level(self, self.data.get('task_type'))
            # 更新page表
            self.db.page.update_one(cond, {'$set': {'chars.$': char}})
            self.send_data_response(dict(txt_logs=char['txt_logs']))
            self.add_log('update_txt', None, char_name, update)

        except self.DbError as error:
            return self.send_db_error(error)


class PageTxtMatchApi(PageHandler):
    URL = ['/api/page/txt_match/@page_name']

    def post(self, page_name):
        """ 提交文本匹配"""
        try:
            r = self.save_txt_match(self, page_name)
            self.send_data_response(r)
        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def save_txt_match(self, page_name):
        rules = [(v.not_empty, 'field', 'content')]
        self.validate(self.data, rules)
        page = self.db.page.find_one({'name': page_name})
        if not page:
            return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
        r = self.check_match(page['chars'], self.data['content'])
        if r['status'] and not self.data.get('only_check'):
            content, field = self.data['content'].replace('\n', '|'), self.data['field']
            chars = self.write_back_txt(page['chars'], content, field)
            self.db.page.update_one({'_id': page['_id']}, {'$set': {
                field: content, 'chars': chars, 'txt_match.%s.status' % field: True,
                'txt_match.%s.value' % field: content,
            }})
        return r


class PageTxtMatchDiffApi(PageHandler):
    URL = '/api/page/txt_match/diff'

    def post(self):
        """ 图文匹配文本比较"""
        try:
            rules = [(v.not_empty, 'texts')]
            self.validate(self.data, rules)
            diff_blocks = self.match_diff(*self.data['texts'])
            cmp_data = self.render_string('com/_txt_diff.html', blocks=diff_blocks,
                                          sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))
            cmp_data = native_str(cmp_data)
            self.send_data_response(dict(cmp_data=cmp_data))

        except self.DbError as error:
            return self.send_db_error(error)


class PageFindCmpTxtApi(PageHandler):
    URL = '/api/page/find_cmp/@page_name'

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
        except Exception as error:
            return self.send_db_error(error)


class PageCmpTxtNeighborApi(PageHandler):
    URL = '/api/page/find_cmp/neighbor'

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


class PageCmpTxtApi(PageHandler):
    URL = '/api/page/cmp_txt/@page_name'

    def post(self, page_name):
        """ 提交比对文本"""
        try:
            rules = [(v.not_empty, 'cmp_txt')]
            self.validate(self.data, rules)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            self.db.page.update_one({'_id': page['_id']}, {'$set': {'cmp_txt': self.data['cmp_txt']}})
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageDetectCharsApi(PageHandler):
    URL = '/api/page/txt/detect_chars'

    def post(self):
        """ 根据文本行内容识别宽字符"""
        try:
            mb4 = [[self.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)

    @classmethod
    def check_utf8mb4(cls, seg, base=None):
        column_strip = re.sub(r'\s', '', base or seg.get('base', ''))
        char_codes = [(c, url_escape(c)) for c in list(column_strip)]
        seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])
        return seg


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
            cmp_data = self.render_string('com/_txt_diff.html', blocks=diff_blocks,
                                          sort_by_key=lambda d: sorted(d.items(), key=lambda t: t[0]))
            cmp_data = native_str(cmp_data)
            self.send_data_response(dict(cmp_data=cmp_data))

        except self.DbError as error:
            return self.send_db_error(error)

    @staticmethod
    def set_hints(diff_blocks, hints):
        for hint in hints:
            line_segments = diff_blocks.get(hint['block_no'], {}).get(hint['line_no'])
            if not line_segments:
                continue
            for s in line_segments:
                if s['base'] == hint['base'] and s['cmp1'] == hint['cmp1']:
                    s['selected'] = True
        return diff_blocks


class PageStartCheckMatchApi(BaseHandler):
    URL = '/api/page/start_check_match'

    def post(self):
        """ 启动检查图文匹配脚本"""
        try:
            rules = [(v.not_empty, 'field', 'publish_task')]
            self.validate(self.data, rules)
            condition = '{}'
            if self.data.get('page_names'):
                condition = ','.join(self.data['page_names'])
            elif self.data.get('search'):
                condition = Page.get_page_search_condition(self.data['search'])[0] or {}
                condition = json.dumps(condition)
            script = "nohup python3 %s/utils/check_match.py --condition='%s' --fields='%s' --publish_task=%s --username=%s >> log/check_match_%s.log 2>&1 &"
            script = script % (h.BASE_DIR, condition, ','.join(self.data['field']), self.data['publish_task'],
                               self.username, h.get_date_time(fmt='%Y%m%d%H%M%S'))
            print(script)
            os.system(script)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class PageStartGenCharsApi(BaseHandler):
    URL = '/api/page/start_gen_chars'

    def post(self):
        """ 批量生成字表"""
        try:
            rules = [(v.not_all_empty, 'page_names', 'search', 'all')]
            self.validate(self.data, rules)
            script = "nohup python3 %s/utils/gen_chars.py %s --username='%s' >> log/gen_chars_%s.log 2>&1 &"
            cond, count = "--condition={}", 0
            if self.data.get('page_names'):
                cond = "--page_names='" + ','.join(self.data['page_names']) + "'"
                count = len(self.data['page_names'])
            elif self.data.get('search'):
                cond = Page.get_page_search_condition(self.data['search'])[0] or {}
                count = self.db.page.count_documents(cond)
                cond = "--condition='" + json.dumps(cond) + "'"
            else:
                count = self.db.page.count_documents({})
            if count:
                script = script % (h.BASE_DIR, cond, self.username, h.get_date_time(fmt='%Y%m%d%H%M%S'))
                print(script)
                os.system(script)
                self.send_data_response(count=count)
            else:
                self.send_error_response(e.no_object, message='找不到对应的页数据')

        except self.DbError as error:
            return self.send_db_error(error)
