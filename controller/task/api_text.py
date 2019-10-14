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
from controller.task.api import FinishTaskApi
from controller.task.view_text import TextTools, TextProofHandler
from controller.data.esearch import find_one, find_neighbor


class GetCompareTextApi(TaskHandler):
    URL = '/api/task/text_proof/get_compare/@page_name'

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


class GetCompareNeighborApi(TaskHandler):
    URL = '/api/task/text_proof/get_compare_neighbor'

    def post(self):
        """ 获取比对文本的前后页文本
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
                    txt=Diff.pre_cmp(''.join(neighbor['_source']['origin'])),
                    code=neighbor['_source']['page_code']
                ))
            else:
                self.send_error_response(errors.no_object, message='没有更多内容')

        except DbError as e:
            self.send_db_error(e)


class SaveTextProofApi(FinishTaskApi):
    URL = ['/api/task/do/text_proof_@num/@page_name',
           '/api/task/update/text_proof_@num/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字校对任务 """
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [
                (v.not_empty, 'step'),
                (v.not_both_empty, 'cmp', 'txt_html'),
                (v.in_list, 'step', list(TextProofHandler.default_steps.keys()))
            ]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                self.send_error_response(errors.no_object)

            # 检查权限
            mode = (re.findall('(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page, 'text_proof_' + num):
                self.send_error_response(errors.data_unauthorized)

            if data['step'] == 'select_compare_text':
                return self.save_compare_text(num, page, mode, data)
            else:
                return self.save_proof(num, page_name, mode, data)

        except DbError as e:
            self.send_db_error(e)

    def save_compare_text(self, num, page, mode, data):
        # 保存数据
        task_type = 'text_proof_' + num
        update = {'tasks.%s.cmp' % task_type: data['cmp'].strip('\n')}
        update.update({'tasks.%s.updated_time' % task_type: datetime.now()})

        # 提交步骤
        if data.get('submit'):
            submitted = self.prop(page, 'tasks.%s.steps.submitted' % task_type) or []
            if data['step'] not in submitted:
                submitted.append(data['step'])
            update.update({'tasks.%s.steps.submitted' % task_type: submitted})
        r = self.db.page.update_one({'name': page['name']}, {'$set': update})
        if r.modified_count:
            self.add_op_log('save_%s_%s' % (mode, task_type), context=page['name'])

        self.send_data_response({'updated': True})

    def save_proof(self, num, page_name, mode, data):
        # 保存数据
        ret = {'updated': True}
        task_type = 'text_proof_' + num
        doubt = data.get('doubt', '').strip('\n')
        update = {'tasks.%s.doubt' % task_type: doubt, 'tasks.%s.updated_time' % task_type: datetime.now()}
        txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
        update.update({'tasks.%s.txt_html' % task_type: txt_html})
        r = self.db.page.update_one({'name': page_name}, {'$set': update})
        if r.modified_count:
            self.add_op_log('save_%s_%s' % (mode, task_type), context=page_name)

        # 提交任务
        if mode == 'do' and data.get('submit'):
            ret.update(self.finish_task(task_type, page_name))

        self.send_data_response(ret)


class SaveTextReviewApi(FinishTaskApi):
    URL = ['/api/task/do/text_review/@page_name',
           '/api/task/update/text_review/@page_name',
           '/api/data/text_edit/@page_name']

    def post(self, page_name):
        """ 文字审定提交 """
        try:
            # 检查权限
            task_type = 'text_review'
            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            # 保存数据
            ret = {'updated': True}
            data = self.get_request_data()
            doubt = data.get('doubt', '').strip('\n')
            update = {'tasks.%s.doubt' % task_type: doubt, 'tasks.%s.updated_time' % task_type: datetime.now()}
            txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
            if txt_html:
                update.update({'txt_html': txt_html})
                update.update({'text': TextTools.html2txt(txt_html)})

            # 生成难字任务
            if mode == 'do' and data.get('submit') and doubt:
                update.update({
                    'tasks.text_hard.status': self.STATUS_OPENED, 'tasks.text_hard.publish_time': datetime.now(),
                })
                self.add_op_log('publish_text_hard', context=page_name)

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_%s_%s' % (mode, task_type), context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.finish_task(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveTextHardApi(FinishTaskApi):
    URL = ['/api/task/do/text_hard/@page_name',
           '/api/task/update/text_hard/@page_name']

    def post(self, page_name):
        """ 难字审定提交 """
        try:
            # 检查权限
            task_type = 'text_hard'
            mode = (re.findall('/(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            # 保存数据
            ret = {'updated': True}
            data = self.get_request_data()
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}
            txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
            if txt_html:
                update.update({'txt_html': txt_html})
                update.update({'text': TextTools.html2txt(txt_html)})

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_%s_%s' % (mode, task_type), context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.finish_task(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)
