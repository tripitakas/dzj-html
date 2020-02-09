#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
from bson import json_util
from tornado.escape import json_decode
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.page.diff import Diff
from controller.page.base import PageHandler
from controller.page.tool import PageTool
from elasticsearch.exceptions import ConnectionTimeout


class CutTaskApi(PageHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    def post(self, task_type, task_id):
        """ 提交切分任务"""

        def get_doc_update():
            update = dict()
            if isinstance(self.data['boxes'], str):
                self.data['boxes'] = json_decode(self.data['boxes'])
            if self.data['step'] == 'orders':
                assert self.data.get('chars_col')
                update['chars'] = self.reorder_chars(self.data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[self.data['step']] = self.sort_boxes(self.data['boxes'], self.data['step'], page=self.page)
            return update

        try:
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', list(self.step2box.keys()))]
            self.validate(self.data, rules)

            self.submit_task(submit=self.data.get('submit'))
            self.submit_doc(get_doc_update(), self.data.get('submit'))

            if self.data.get('config'):
                self.set_secure_cookie('%s_%s' % (task_type, self.data['step']), json_util.dumps(self.data['config']))

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class CutEditApi(PageHandler):
    URL = '/api/task/cut_edit/@page_name'

    def post(self, page_name):
        """ 修改切分数据"""

        def get_doc_update():
            update = dict()
            if isinstance(self.data['boxes'], str):
                self.data['boxes'] = json_decode(self.data['boxes'])
            if self.data['step'] == 'orders':
                assert self.data.get('chars_col')
                update['chars'] = self.reorder_chars(self.data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[self.data['step']] = self.sort_boxes(self.data['boxes'], self.data['step'], page=self.page)
            return update

        try:
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', list(self.step2box.keys()))]
            self.validate(self.data, rules)

            info = get_doc_update()
            release_lock = self.data.get('submit') and self.steps['is_last']
            self.update_edit_doc(self.task_type, doc_id=page_name, release_lock=release_lock, info=info)

            self.add_op_log('edit_box', target_id=self.page['_id'], context=page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class TextProofApi(PageHandler):
    URL = ['/api/task/do/text_proof_@num/@task_id',
           '/api/task/update/text_proof_@num/@task_id']

    def post(self, num, task_id):
        """ 保存或提交文字校对任务"""
        try:
            rules = [(v.not_empty, 'step'), (v.in_list, 'step', self.get_steps(self.task_type))]
            self.validate(self.data, rules)

            if self.steps['current'] == 'select':
                self.save_select(self.data)
            else:
                self.save_proof(self.data)

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
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
        self.submit_task(info, data.get('submit'))
        self.submit_doc({}, data.get('submit'))
        if data.get('submit') and self.mode == 'update':
            self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)


class TextReviewApi(PageHandler):
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
        """ 文字审定提交 """
        try:
            doubt = self.data.get('doubt', '').strip('\n')
            # 发布难字任务
            if self.data.get('submit') and self.mode == 'do':
                self.publish_hard_task(self.task, doubt)
            # 更新当前任务
            info = {'result.doubt': doubt, 'updated_time': self.now()}
            self.submit_task(info, self.data.get('submit'))
            # 更新数据
            txt_html = self.data.get('txt_html', '').strip('\n')
            info = self.get_txt_html_update(txt_html)
            self.submit_doc(info, self.data.get('submit'))

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class TextHardApi(PageHandler):
    URL = ['/api/task/do/text_hard/@task_id',
           '/api/task/update/text_hard/@task_id']

    def post(self, task_id):
        """ 难字审定提交"""
        try:
            # 更新任务
            doubt = self.data.get('doubt', '').strip('\n')
            info = {'result.doubt': doubt, 'updated_time': self.now()}
            self.submit_task(info, self.data.get('submit'))
            # 更新数据
            txt_html = self.data.get('txt_html', '').strip('\n')
            info = self.get_txt_html_update(txt_html)
            self.submit_doc(info, self.data.get('submit'))

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class TextEditApi(PageHandler):
    URL = '/api/task/text_edit/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
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

        except DbError as error:
            return self.send_db_error(error)


class DetectWideCharsApi(PageHandler):
    URL = '/api/task/detect_chars'

    def post(self):
        """根据文本行内容识别宽字符"""
        try:
            mb4 = [[PageTool.check_utf8mb4({}, t)['utf8mb4'] for t in s] for s in self.data['texts']]
            self.send_data_response(mb4)
        except Exception as error:
            return self.send_db_error(error)


class GenCharIdApi(PageHandler):
    URL = '/api/cut/gen_char_id'

    def post(self):
        """ 根据坐标重新生成栏、列、字框的编号"""
        chars = self.data['chars']
        blocks = self.data['blocks']
        columns = self.data['columns']
        # 每列字框的序号 [[char_index_of_col1, ...], col2...]
        chars_col = self.data.get('chars_col')
        zero_char_id, layout_type = [], self.data.get('layout_type')
        r = self.calc(blocks, columns, chars, chars_col, layout_type)
        if r:
            zero_char_id, layout_type, chars_col = r

        return self.send_data_response(dict(
            blocks=blocks, columns=columns, chars=chars, chars_col=chars_col,
            zero_char_id=zero_char_id, layout_type=layout_type
        ))


class SelectTextApi(PageHandler):
    URL = '/api/task/text_select/@page_name'

    def post(self, page_name):
        """ 获取比对本。根据OCR文本，从CBETA库中获取相似的文本作为比对本"""
        from controller.com.esearch import find_one
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

        except DbError as error:
            return self.send_db_error(error)
        except ConnectionTimeout as error:
            return self.send_db_error(error)


class NeighborTextApi(PageHandler):
    URL = '/api/task/text_neighbor'

    def post(self):
        """ 获取比对文本的前后页文本"""
        # param page_code: 当前cmp文本的page_code（对应于es库中的page_code）
        # param neighbor: prev/next，根据当前cmp文本的page_code往前或者往后找一条数据
        from controller.com.esearch import find_neighbor
        try:
            rules = [(v.not_empty, 'cmp_page_code', 'neighbor')]
            self.validate(self.data, rules)

            neighbor = find_neighbor(self.data.get('cmp_page_code'), self.data.get('neighbor'))
            if neighbor:
                txt = Diff.pre_cmp(''.join(neighbor['_source']['origin']))
                self.send_data_response(dict(txt=txt, code=neighbor['_source']['page_code']))
            else:
                self.send_error_response(e.no_object, message='没有更多内容')

        except DbError as error:
            return self.send_db_error(error)
