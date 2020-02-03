#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
from bson import json_util
from datetime import datetime
from tornado.escape import json_decode
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.page.diff import Diff
from controller.page.base import PageHandler
from elasticsearch.exceptions import ConnectionTimeout


class CutTaskApi(PageHandler):
    URL = ['/api/task/do/@cut_task/@task_id',
           '/api/task/update/@cut_task/@task_id']

    def post(self, task_type, task_id):
        """ 提交切分任务"""
        try:
            data = self.get_request_data()
            steps = list(self.step2box.keys())
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', steps)]
            self.validate(data, rules)
            # 更新page
            update = dict()
            data['boxes'] = json_decode(data['boxes']) if isinstance(data['boxes'], str) else data['boxes']
            if data['step'] == 'orders':
                assert data.get('chars_col')
                update['chars'] = self.reorder_chars(data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[data['step']] = self.sort_boxes(data['boxes'], data['step'], page=self.page)
            self.db.page.update_one({'name': self.task['doc_id']}, {'$set': update})
            # 检查config
            if data.get('config'):
                self.set_secure_cookie('%s_%s' % (task_type, data['step']), json_util.dumps(data['config']))
            # 提交任务
            if data.get('submit'):
                self.submit_task(data)

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class CutEditApi(PageHandler):
    URL = '/api/page/edit/box/@page_name'

    def post(self, page_name):
        """ 修改切分数据"""
        try:
            data = self.get_request_data()
            steps = list(self.step2box.keys())
            rules = [(v.not_empty, 'step', 'boxes'), (v.in_list, 'step', steps)]
            self.validate(data, rules)

            update = dict()
            data['boxes'] = json_decode(data['boxes']) if isinstance(data['boxes'], str) else data['boxes']
            if data['step'] == 'orders':
                assert data.get('chars_col')
                update['chars'] = self.reorder_chars(data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[data['step']] = self.sort_boxes(data['boxes'], data['step'], page=self.page)
            self.db.page.update_one({'name': self.page_name}, {'$set': update})
            self.add_op_log('edit_box', target_id=self.page['_id'], context=page_name)

            if data.get('submit'):
                self.release_temp_lock(page_name, 'box', self.current_user)

            self.add_op_log('edit_box', target_id=page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class TextProofApi(PageHandler):
    URL = ['/api/task/do/text_proof_@num/@task_id',
           '/api/task/update/text_proof_@num/@task_id']

    def post(self, num, task_id):
        """ 保存或提交文字校对任务"""
        try:
            data = self.get_request_data()
            rules = [
                (v.not_empty, 'step'),
                (v.not_both_empty, 'cmp', 'txt_html'),
                (v.in_list, 'step', self.get_steps(self.task_type)),
            ]
            self.validate(data, rules)

            if data['step'] == 'select':
                self.save_select(data)
            else:
                self.save_proof(data)

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)

        except DbError as error:
            return self.send_db_error(error)

    def save_select(self, data):
        update = {'result.cmp': data['cmp'].strip('\n'), 'updated_time': datetime.now()}
        if data.get('submit'):
            update.update({'steps.submitted': self.get_submitted(data['step'])})
        self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
        self.add_op_log('save_task', target_id=self.task['_id'], context=self.task['doc_id'])

    def save_proof(self, data):
        doubt = data.get('doubt', '').strip('\n')
        txt_html = data.get('txt_html', '').strip('\n')
        update = {'result.doubt': doubt, 'result.txt_html': txt_html, 'updated_time': datetime.now()}
        self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
        self.add_op_log('save_task', target_id=self.task['_id'], context=self.task['doc_id'])
        if data.get('submit'):
            if self.mode == 'do':
                self.finish_task(self.task)
            else:
                self.release_temp_lock(self.task['doc_id'], 'box', self.current_user)
        self.send_data_response()


class TextReviewApi(PageHandler):
    URL = ['/api/task/do/text_review/@task_id',
           '/api/task/update/text_review/@task_id']

    def publish_hard_task(self, review_task, doubt):
        """ 发布难字任务。如果审定任务已完成，或者存疑为空，则跳过"""
        if not doubt or review_task['task_type'] == self.STATUS_FINISHED:
            return
        now = datetime.now()
        task = dict(task_type='text_hard', collection='page', id_name='name', doc_id=review_task['doc_id'],
                    status=self.STATUS_PUBLISHED, priority=review_task['priority'], steps={'todo': []},
                    pre_tasks={}, input={'review_task': review_task['_id']}, result={'doubt': doubt},
                    create_time=now, updated_time=now, publish_time=now,
                    publish_user_id=self.current_user['_id'],
                    publish_by=self.current_user['name'])
        r = self.db.task.insert_one(task)
        self.add_op_log('publish_task', target_id=r.inserted_id, context=str(review_task['_id']))
        return r.inserted_id

    def post(self, task_id):
        """ 文字审定提交 """
        try:
            data = self.get_request_data()
            # 更新任务
            doubt = data.get('doubt', '').strip('\n')
            update = {'result.doubt': doubt, 'updated_time': datetime.now()}
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
            if data.get('submit'):
                if self.mode == 'do':
                    self.publish_hard_task(self.task, doubt)
                    self.finish_task(self.task)
                else:
                    self.release_temp_lock(self.page_name, 'text', self.current_user)
            # 更新page
            txt_html = data.get('txt_html', '').strip('\n')
            self.update_page_txt_html(txt_html)

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
            data = self.get_request_data()
            doubt = data.get('doubt', '').strip('\n')
            update = {'result.doubt': doubt, 'updated_time': datetime.now()}
            self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
            if data.get('submit'):
                if self.mode == 'do':
                    self.finish_task(self.task)
                else:
                    self.release_temp_lock(self.page_name, 'text', self.current_user)
            # 更新page
            txt_html = data.get('txt_html', '').strip('\n')
            self.update_page_txt_html(txt_html)

            self.add_op_log(self.mode + '_task', target_id=self.task_id, context=self.page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class TextEditApi(PageHandler):
    URL = '/api/page/edit/text/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'txt_html')]
            self.validate(data, rules)
            # 更新page
            txt_html = data.get('txt_html', '').strip('\n')
            self.update_page_txt_html(txt_html)
            if data.get('submit'):
                self.release_temp_lock(page_name, 'text', self.current_user)

            self.add_op_log('edit_text', target_id=page_name)
            self.send_data_response()

        except DbError as error:
            return self.send_db_error(error)


class GenCharIdApi(PageHandler):
    URL = '/api/cut/gen_char_id'

    def post(self):
        """ 根据坐标重新生成栏、列、字框的编号"""
        data = self.get_request_data()
        chars = data['chars']
        blocks = data['blocks']
        columns = data['columns']
        # 每列字框的序号 [[char_index_of_col1, ...], col2...]
        chars_col = data.get('chars_col')
        zero_char_id, layout_type = [], data.get('layout_type')
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
        from controller.tool.esearch import find_one
        try:
            ocr = self.get_ocr()
            num = self.prop(self.get_request_data(), 'num', 1)
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
        from controller.tool.esearch import find_neighbor
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'cmp_page_code', 'neighbor')]
            self.validate(data, rules)

            neighbor = find_neighbor(data.get('cmp_page_code'), data.get('neighbor'))
            if neighbor:
                txt = Diff.pre_cmp(''.join(neighbor['_source']['origin']))
                self.send_data_response(dict(txt=txt, code=neighbor['_source']['page_code']))
            else:
                self.send_error_response(e.no_object, message='没有更多内容')

        except DbError as error:
            return self.send_db_error(error)
