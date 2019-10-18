#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import json_decode
import controller.validate as v
import controller.errors as errors
from controller.base import DbError
from controller.task.base import TaskHandler
from controller.text.diff import Diff
from controller.text.view import TextTools, TextProofHandler


class GetCompareTextApi(TaskHandler):
    URL = '/api/task/text_proof/get_compare/@page_name'

    def post(self, page_name):
        """ 获取ocr对应的比对文本 """
        from controller.search.esearch import find_one
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
        from controller.search.esearch import find_neighbor
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


class SaveTextProofApi(TaskHandler):
    URL = ['/api/task/do/text_proof_@num/@task_id',
           '/api/task/update/text_proof_@num/@task_id']

    def post(self, num, task_id):
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

            task_type = 'text_proof_' + num
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.send_error_response(errors.no_object)

            # 检查权限
            mode = (re.findall('(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(task, mode):
                return self.send_error_response(errors.data_unauthorized)

            if data['step'] == 'select_compare_text':
                return self.save_compare_text(task, mode, data)
            else:
                return self.save_proof(task, mode, data)

        except DbError as e:
            self.send_db_error(e)

    def save_compare_text(self, task, mode, data):
        result = task.get('result') or {}
        result.update({'cmp': data['cmp'].strip('\n')})
        update = {'result': result, 'updated_time': datetime.now()}
        if data.get('submit'):
            submitted = self.prop(task, 'steps.submitted') or []
            if data['step'] not in submitted:
                submitted.append(data['step'])
            update.update({'steps.submitted': submitted})
        r = self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        if r.modified_count:
            self.add_op_log('save_%s_%s' % (mode, task['task_type']), context=task['doc_id'])

        self.send_data_response({'updated': True})

    def save_proof(self, task, mode, data):
        # 保存数据
        ret = {'updated': True}
        doubt = data.get('doubt', '').strip('\n')
        txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
        update = {'result.doubt': doubt, 'updated_time': datetime.now(), 'result.txt_html': txt_html}
        r = self.db.task.update_one({'_id': task['_id']}, {'$set': update})
        if r.modified_count:
            self.add_op_log('save_%s_%s' % (mode, task['task_type']), context=task['doc_id'])

        # 提交任务
        if mode == 'do' and data.get('submit'):
            ret.update(self.finish_task(task))

        self.send_data_response(ret)


class SaveTextReviewApi(TaskHandler):
    URL = ['/api/task/do/text_review/@task_id',
           '/api/task/update/text_review/@task_id',
           '/api/data/edit/text/@page_name']

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


class SaveTextHardApi(TaskHandler):
    URL = ['/api/task/do/text_hard/@task_id',
           '/api/task/update/text_hard/@task_id']

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
