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
from controller.task.api_base import SubmitTaskApi
from controller.task.view_text import TextBaseHandler
from controller.data.cbeta_search import find_one, find_neighbor


class GetCmpTextApi(TaskHandler):
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


class GetCmpNeighborApi(TaskHandler):
    URL = '/api/task/text_proof/get_cmp_neighbor'

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


class SaveCmpTextApi(TaskHandler):
    URL = ['/api/task/do/text_proof_@num/find_cmp/@page_name',
           '/api/task/update/text_proof_@num/find_cmp/@page_name']

    def post(self, num, page_name):
        """ 文字校对-选择比对文本提交 """
        try:
            task_type = 'text_proof_' + num
            mode = 'do' if '/do' in self.request.path else 'update'
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            data = self.get_request_data()
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}
            txt = data.get('cmp', '').strip('\n')
            data_field = TextBaseHandler.cmp_fields.get(task_type)
            if txt:
                update.update({data_field: txt})

            if mode == 'do' and data.get('commit'):
                update.update({'tasks.%s.committed' % task_type: ['find_cmp']})
                ret['committed'] = True

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveTextProofApi(SubmitTaskApi):
    URL = ['/api/task/do/text_proof_@num/@page_name',
           '/api/task/update/text_proof_@num/@page_name']

    def post(self, num, page_name):
        """ 保存或提交文字校对任务 """
        try:
            # 保存任务
            task_type = 'text_proof_' + num
            assert task_type in self.text_task_names()
            mode = 'do' if '/do' in self.request.path else 'update'
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            data = self.get_request_data()
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}
            txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
            data_field = TextBaseHandler.save_fields.get(task_type)
            if txt_html:
                update.update({data_field: txt_html})

            doubt = data.get('doubt')
            if doubt:
                update.update({'tasks.%s.doubt' % task_type: doubt.strip('\n')})

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveTextReviewApi(SubmitTaskApi):
    URL = ['/api/task/do/text_review/@page_name',
           '/api/task/update/text_review/@page_name',
           '/api/data/edit/text/@page_name']

    def post(self, page_name):
        """ 文字审定提交 """
        try:
            # 保存任务
            task_type = 'text_review'
            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            data = self.get_request_data()
            doubt = data.get('doubt', '').strip('\n')
            update = {'tasks.%s.doubt' % task_type: doubt, 'tasks.%s.updated_time' % task_type: datetime.now()}
            txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
            data_field = TextBaseHandler.save_fields.get(task_type)
            if txt_html:
                update.update({data_field: txt_html})
                update.update({'text': TextBaseHandler.get_txt_from_html(txt_html)})

            if mode == 'do' and data.get('submit') and doubt:  # 生成难字任务
                update.update({
                    'tasks.text_hard.status': self.STATUS_OPENED,'tasks.text_hard.publish_time': datetime.now(),
                })
                ret['text_hard'] = True

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)


class SaveTextHardApi(SubmitTaskApi):
    URL = ['/api/task/do/text_hard/@page_name',
           '/api/task/update/text_hard/@page_name']

    def post(self, page_name):
        """ 难字审定提交 """
        try:
            # 保存任务
            task_type = 'text_hard'
            mode = (re.findall('/(do|update)/', self.request.path) or ['do'])[0]
            if not self.check_auth(mode, page_name, task_type):
                self.send_error_response(errors.data_unauthorized)

            ret = {'updated': True}
            data = self.get_request_data()
            update = {'tasks.%s.updated_time' % task_type: datetime.now()}
            txt_html = data.get('txt_html') and re.sub(r'\|+$', '', json_decode(data['txt_html']).strip('\n'))
            data_field = TextBaseHandler.save_fields.get(task_type)
            if txt_html:
                update.update({data_field: txt_html})
                update.update({'text': TextBaseHandler.get_txt_from_html(txt_html)})

            r = self.db.page.update_one({'name': page_name}, {'$set': update})
            if r.modified_count:
                self.add_op_log('save_' + task_type, context=page_name)

            # 提交任务
            if mode == 'do' and data.get('submit'):
                ret.update(self.submit(task_type, page_name))

            self.send_data_response(ret)

        except DbError as e:
            self.send_db_error(e)
