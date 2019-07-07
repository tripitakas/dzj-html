#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
import controller.validate as v
import controller.errors as errors
from controller.base import DbError
from controller.data.diff import Diff
from tornado.escape import json_decode
from controller.task.base import TaskHandler
from controller.data.cbeta_search import find_one, find_neighbor


class TextApi(TaskHandler):
    """ 保存数据。有do/update两种模式。1. do。做任务时，保存或提交任务。2. update。任务完成后，本任务用户修改数据。
        不提供其他人修改，因此仅检查任务归属，无需检查数据锁。
    """
    cmp_fields = {
        'text_proof_1': 'cmp1',
        'text_proof_2': 'cmp2',
        'text_proof_3': 'cmp3'
    }
    save_fields = {
        'text_proof_1': 'txt1_html',
        'text_proof_2': 'txt2_html',
        'text_proof_3': 'txt3_html',
        'text_review': 'txt_review_html'
    }

    def save(self, task_type, page_name, mode):
        try:
            assert task_type in self.text_task_names() and mode in ['do', 'update', 'edit']

            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            data, ret = self.get_request_data(), {'updated': True}
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}

            txt = data.get('txt') and re.sub(r'\|+$', '', json_decode(data['txt']).strip('\n'))
            data_field = self.save_fields.get(task_type)
            if txt:
                update.update({data_field: txt})

            doubt = self.get_request_data().get('doubt', '').strip('\n')
            if doubt:
                update.update({'tasks.%s.doubt' % task_type: doubt})

            if mode == 'do' and data.get('submit'):
                update.update({
                    'tasks.%s.status' % task_type: self.STATUS_FINISHED,
                    'tasks.%s.finished_time' % task_type: datetime.now(),
                })
                ret['submitted'] = True

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            if mode == 'do' and data.get('submit'):
                # 处理后置任务
                self.update_post_tasks(page_name, task_type)
                ret['post_tasks_updated'] = True

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveTextProofApi(TextApi):
    URL = ['/api/task/do/text_proof_@num/@page_name',
           '/api/task/update/text_proof_@num/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字校对任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update'
        self.save('text_proof_' + num, page_name, mode=mode)


class SaveTextReviewApi(TextApi):
    URL = ['/api/task/do/text_review/@page_name',
           '/api/task/update/text_review/@page_name']

    def post(self, page_name):
        """ 保存或提交文字审定任务 """
        p = self.request.path
        mode = 'do' if '/do' in p else 'update'
        self.save('text_review', page_name, mode=mode)


class SaveCmpTextApi(TextApi):
    URL = ['/api/task/do/text_proof_@num/find_cmp/@page_name',
           '/api/task/update/text_proof_@num/find_cmp/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字校对-选择比对本数据 """
        try:
            p = self.request.path
            mode = 'do' if '/do' in p else 'update'
            task_type = 'text_proof_' + num
            assert task_type in self.text_task_names() and mode in ['do', 'update']

            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            data, ret = self.get_request_data(), {'updated': True}
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}

            txt = data.get('cmp')
            data_field = self.cmp_fields.get(task_type)
            if txt:
                update.update({data_field: txt.strip('\n')})

            if mode == 'do' and data.get('commit'):
                update.update({
                    'tasks.%s.committed' % task_type: ['find_cmp']
                })
                ret['committed'] = True

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class GetCmpTextApi(TextApi):
    URL = '/api/task/text_proof/get_cmp/@page_name'

    def post(self, page_name):
        """ 获取ocr对应的比对文本 """
        try:
            page = self.db.page.find_one({'name': page_name})
            if page:
                num = self.get_request_data().get('num') or 1
                cmp, hit_page_codes = find_one(page.get('ocr'), int(num))
                if cmp:
                    self.send_data_response(dict(cmp=cmp, hit_page_codes=hit_page_codes))
                else:
                    self.send_error_response(errors.no_object, message='未找到比对文本')
            else:
                self.send_error_response(errors.no_object, message='页面%s不存在' % page_name)

        except DbError as e:
            self.send_db_error(e)


class GetCmpNeighborApi(TextApi):
    URL = '/api/task/text_proof/get_cmp_neighbor'

    def post(self):
        """ 获取ocr对应的比对文本
        :param page_code: 当前cmp文本的page_code（es库中的page_code）
        :param neighbor: prev/next，根据当前cmp文本的page_code往前或者往后找一条数据
        """
        try:
            data = self.get_request_data()
            err = v.validate(data, [(v.not_empty, 'cmp_page_code', 'neighbor')])
            if err:
                return self.send_error_response(err)

            neighbor = find_neighbor(data.get('cmp_page_code'), data.get('neighbor'))
            if neighbor:
                self.send_data_response(dict(
                    txt=Diff.pre_cmp(''.join(neighbor['_source']['origin'])), code=neighbor['_source']['page_code']
                ))
            else:
                self.send_error_response(errors.no_object, message='页面不存在')

        except DbError as e:
            self.send_db_error(e)
