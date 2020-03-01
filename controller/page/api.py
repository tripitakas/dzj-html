#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.escape import native_str
from controller import errors as e
from controller import validate as v
from .tool.diff import Diff
from .base import PageHandler
from .tool.esearch import find_one, find_neighbor
from elasticsearch.exceptions import ConnectionTimeout


class TaskCutApi(PageHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    def post(self, task_type, task_id):
        """ 提交切分校对任务"""

        try:
            if self.steps['current'] == 'order':
                self.save_order()
            else:
                self.save_box()
            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)

        except self.DbError as error:
            return self.send_db_error(error)

    def save_box(self):
        rules = [(v.not_empty, 'blocks', 'columns', 'chars')]
        self.validate(self.data, rules)
        self.update_task(self.data.get('submit'))
        # 要提前检查，否则char_id可能重新设置
        valid, message, out_boxes = self.check_box_cover(self.page)
        update = self.get_box_update()
        self.update_my_doc(update)
        self.send_data_response(dict(valid=valid, message=message, out_boxes=out_boxes))

    def save_order(self):
        self.validate(self.data, [(v.not_empty, 'chars_col')])
        self.update_task(self.data.get('submit'))
        if not self.cmp_char_cid(self.page['chars'], self.data['chars_col']):
            return self.send_error_response(e.cid_not_identical, message='检测到字框有增减，请刷新页面')
        if len(self.data['chars_col']) != len(self.page['columns']):
            return self.send_error_response(e.col_not_identical, message='提交的字序中列数有变化，请检查')
        chars = self.update_char_order(self.page['chars'], self.data['chars_col'])
        self.update_my_doc(dict(chars=chars, chars_col=self.data['chars_col']))
        self.send_data_response()


class CutEditApi(PageHandler):
    URL = '/api/page/cut_edit/@page_name'

    def post(self, page_name):
        """ 修改切分数据"""

        try:
            if self.steps['current'] == 'order':
                self.save_order(page_name)
            else:
                self.save_box(page_name)
            self.add_op_log('edit_box', target_id=self.page['_id'], context=page_name)

        except self.DbError as error:
            return self.send_db_error(error)

    def save_box(self, page_name):
        rules = [(v.not_empty, 'blocks', 'columns', 'chars')]
        self.validate(self.data, rules)
        # 要提前检查，否则char_id可能重新设置
        valid, message, out_boxes = self.check_box_cover(self.page)
        update = self.get_box_update()
        self.update_edit_doc(self.task_type, page_name, self.data.get('submit'), update)
        self.send_data_response(dict(valid=valid, message=message, out_boxes=out_boxes))

    def save_order(self, page_name):
        self.validate(self.data, [(v.not_empty, 'chars_col')])
        if not self.cmp_char_cid(self.page['chars'], self.data['chars_col']):
            return self.send_error_response(e.cid_not_identical, message='检测到字框有增减，请刷新页面')
        if len(self.data['chars_col']) != len(self.page['columns']):
            return self.send_error_response(e.col_not_identical, message='提交的字序中列数有变化，请检查')
        chars = self.update_char_order(self.page['chars'], self.data['chars_col'])
        update = dict(chars=chars, chars_col=self.data['chars_col'])
        self.update_edit_doc(self.task_type, page_name, self.data.get('submit'), update)
        self.send_data_response()


class TaskTextProofApi(PageHandler):
    URL = ['/api/task/do/text_proof_@num/@task_id',
           '/api/task/update/text_proof_@num/@task_id']

    def post(self, num, task_id):
        """ 提交文字校对任务"""
        try:
            rules = [(v.not_empty, 'step'), (v.in_list, 'step', self.get_steps(self.task_type))]
            self.validate(self.data, rules)

            if self.steps['current'] == 'select':
                self.save_select(self.data)
            else:
                self.save_proof(self.data)

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)

    def save_select(self, data):
        update = {'result.cmp': data.get('cmp', '').strip('\n'), 'updated_time': self.now()}
        if data.get('submit'):
            update.update({'steps.submitted': self.get_submitted(data['step'])})
        self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})

    def save_proof(self, data):
        doubt = data.get('doubt', '').strip('\n')
        txt_html = data.get('txt_html', '').strip('\n')
        info = {'result.doubt': doubt, 'result.txt_html': txt_html, 'updated_time': self.now()}
        self.update_task(data.get('submit'), info)
        self.update_my_doc({}, data.get('submit'))
        if data.get('submit') and self.mode == 'update':
            self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)


class TaskTextReviewApi(PageHandler):
    URL = ['/api/task/do/text_review/@task_id',
           '/api/task/update/text_review/@task_id']

    def publish_hard_task(self, review_task, doubt):
        """ 发布难字任务。如果审定任务已完成，或者存疑为空，则跳过"""
        if not doubt or review_task['task_type'] == self.STATUS_FINISHED:
            return
        task = dict(task_type='text_hard', collection='page', id_name='name', doc_id=review_task['doc_id'],
                    status=self.STATUS_PUBLISHED, priority=review_task['priority'], steps={'todo': []},
                    pre_tasks={}, input={'review_task': review_task['_id']}, result={'doubt': doubt},
                    create_time=self.now(), updated_time=self.now(), publish_time=self.now(),
                    publish_user_id=self.user_id,
                    publish_by=self.username)
        r = self.db.task.insert_one(task)
        self.add_op_log('publish_task', target_id=r.inserted_id, context=str(review_task['_id']))
        return r.inserted_id

    def post(self, task_id):
        """ 提交文字审定任务"""
        try:
            doubt = self.data.get('doubt', '').strip('\n')
            # 发布难字任务
            if self.data.get('submit') and self.mode == 'do':
                self.publish_hard_task(self.task, doubt)
            # 更新当前任务
            info = {'result.doubt': doubt, 'updated_time': self.now()}
            self.update_task(self.data.get('submit'), info)
            # 更新数据
            txt_html = self.data.get('txt_html', '').strip('\n')
            info = self.get_txt_html_update(txt_html)
            self.update_my_doc(info, self.data.get('submit'))

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class TaskTextHardApi(PageHandler):
    URL = ['/api/task/do/text_hard/@task_id',
           '/api/task/update/text_hard/@task_id']

    def post(self, task_id):
        """ 提交难字审定任务"""
        try:
            # 更新任务
            doubt = self.data.get('doubt', '').strip('\n')
            info = {'result.doubt': doubt, 'updated_time': self.now()}
            self.update_task(self.data.get('submit'), info)
            # 更新数据
            txt_html = self.data.get('txt_html', '').strip('\n')
            info = self.get_txt_html_update(txt_html)
            self.update_my_doc(info, self.data.get('submit'))

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class TextEditApi(PageHandler):
    URL = '/api/page/text_edit/@page_name'

    def post(self, page_name):
        """ 修改审定文本"""
        try:
            rules = [(v.not_empty, 'txt_html')]
            self.validate(self.data, rules)

            txt_html = self.data.get('txt_html', '').strip('\n')
            info = self.get_txt_html_update(txt_html)
            if not self.page.get('txt_html'):  # 如果页面原先没有txt_html字段，则去掉这个字段
                info.pop('txt_html', 0)
            self.update_edit_doc(self.task_type, page_name, self.data.get('submit'), info)
            self.add_op_log('edit_text', target_id=page_name)
            self.send_data_response()

        except self.DbError as error:
            return self.send_db_error(error)


class TaskTextSelectApi(PageHandler):
    URL = '/api/task/text_select/@page_name'

    def post(self, page_name):
        """ 寻找比对本。根据OCR文本从CBETA库中查找相似文本作为比对本"""
        try:
            self.page = self.db.page.find_one({'name': page_name})
            if not self.page:
                return self.send_error_response(e.no_object, message='没有找到页面%s' % page_name)
            ocr = self.get_ocr()
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


class TextNeighborApi(PageHandler):
    URL = '/api/page/text_neighbor'

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


class TextsDiffApi(PageHandler):
    URL = '/api/page/diff'

    def post(self):
        """ 用户提交纯文本后重新比较，并设置修改痕迹"""
        try:
            rules = [(v.not_empty, 'texts')]
            self.validate(self.data, rules)
            diff_blocks = self.diff(*self.data['texts'])
            if self.data['hints']:
                diff_blocks = self.set_hints(diff_blocks, self.data['hints'])
            cmp_data = self.render_string('page_text_area.html', blocks=diff_blocks)
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
    URL = '/api/page/detect_chars'

    def post(self):
        """ 根据文本行内容识别宽字符"""
        try:
            mb4 = [[self.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)
