#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from bson.objectid import ObjectId
from tornado.escape import json_decode
from elasticsearch.exceptions import ConnectionTimeout
from controller import validate as v
from controller import errors as errors
from controller.base import DbError
from controller.text.diff import Diff
from controller.task.base import TaskHandler
from controller.text.texttool import TextTool


class GetCompareTextApi(TaskHandler):
    URL = '/api/task/text_get_compare/@page_name'

    def post(self, page_name):
        """ 获取比对本
        根据OCR文本，从CBETA库中获取相似的文本作为比对本"""
        from controller.tool.esearch import find_one
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
        except ConnectionTimeout as e:
            self.send_db_error(e)


class GetCompareNeighborApi(TaskHandler):
    URL = '/api/task/text_compare_neighbor'

    def post(self):
        """ 获取比对文本的前后页文本
        :param page_code: 当前cmp文本的page_code（es库中的page_code）
        :param neighbor: prev/next，根据当前cmp文本的page_code往前或者往后找一条数据
        """
        from controller.tool.esearch import find_neighbor
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


class TextProofApi(TaskHandler):
    URL = ['/api/task/do/text_proof_@num/@task_id',
           '/api/task/update/text_proof_@num/@task_id']

    def post(self, num, task_id):
        """ 保存或提交文字校对任务 """
        try:
            # 检查参数
            data = self.get_request_data()
            task_type = 'text_proof_' + num
            steps = [s[0] for s in self.task_types[task_type].get('steps')]
            rules = [
                (v.not_empty, 'step'),
                (v.in_list, 'step', steps),
                (v.not_both_empty, 'cmp', 'txt_html')
            ]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)

            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.send_error_response(errors.no_object, message='任务不存在')

            # 检查权限
            mode = 'do' if '/task/do' in self.request.path else 'update'
            self.check_task_auth(task, mode)

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
            self.add_op_log('save_%s' % task['task_type'], context=task['doc_id'], target_id=task['_id'])

        self.send_data_response()

    def save_proof(self, task, mode, data):
        # 保存数据
        doubt = data.get('doubt', '').strip('\n')
        txt_html = data.get('txt_html', '').strip('\n')
        r = self.db.task.update_one({'_id': task['_id']}, {'$set': {
            'result.doubt': doubt, 'result.txt_html': txt_html, 'updated_time': datetime.now()
        }})
        if r.modified_count:
            self.add_op_log('save_%s' % task['task_type'], context=task['doc_id'], target_id=task['_id'])

        # 提交任务
        if data.get('submit'):
            if mode == 'do':
                self.finish_task(task)
                self.add_op_log('submit_%s' % task['task_type'], target_id=task['_id'])
            else:
                self.release_temp_lock(task['doc_id'], shared_field='box')

        self.send_data_response()


class TextReviewApi(TaskHandler):
    URL = ['/api/task/do/text_review/@task_id',
           '/api/task/update/text_review/@task_id']

    def publish_hard_task(self, review_task, doubt):
        """ 发布难字任务"""
        now = datetime.now()
        task = dict(task_type='text_hard', collection='page', id_name='name', doc_id=review_task['doc_id'],
                    status=self.STATUS_OPENED, priority=review_task['priority'], steps={'todo': []},
                    pre_tasks={}, input={'review_task': review_task['_id']}, result={'doubt': doubt},
                    create_time=now, updated_time=now, publish_time=now,
                    publish_user_id=self.current_user['_id'],
                    publish_by=self.current_user['name'])
        r = self.db.task.insert_one(task)
        self.add_op_log('publish_text_hard', context=str(review_task['_id']), target_id=r.inserted_id)
        return r.inserted_id

    def post(self, task_id):
        """ 文字审定提交 """

        try:
            task_type = 'text_review'
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.send_error_response(errors.no_object, message='任务不存在')
            # 检查任务权限及数据锁
            mode = 'do' if '/do' in self.request.path else 'update'
            self.check_task_auth(task, mode)
            r = self.check_task_lock(task, mode)
            if r is not True:
                return self.send_error_response(r)
            # 保存当前任务
            data = self.get_request_data()
            doubt = data.get('doubt', '').strip('\n')
            update = {'result.doubt': doubt, 'updated_time': datetime.now()}
            # 生成难字任务（注意，难字任务只能生成一次）
            if data.get('submit') and doubt and not self.prop(task, 'result.hard_task'):
                update['result.hard_task'] = self.publish_hard_task(task, doubt)
            self.db.task.update_one({'_id': task['_id']}, {'$set': update})
            # 将数据结果同步到page中
            txt_html = data.get('txt_html', '').strip('\n')
            text = TextTool.html2txt(txt_html)
            self.db.page.update_one({'name': task['doc_id']}, {'$set': {'text': text, 'txt_html': txt_html}})

            if data.get('submit'):
                if mode == 'do':
                    self.finish_task(task)  # do提交后，完成任务且释放数据锁
                    self.add_op_log('submit_%s' % task_type, target_id=task_id)
                else:
                    self.release_temp_lock(task['doc_id'], shared_field='text')  # update/edit提交后，释放数据锁

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class TextHardApi(TaskHandler):
    URL = ['/api/task/do/text_hard/@task_id',
           '/api/task/update/text_hard/@task_id']

    def post(self, task_id):
        """ 难字审定提交，难字任务的结果存入文字审定的结果中"""
        try:
            task_type = 'text_hard'
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.send_error_response(errors.no_object, message='任务不存在')

            # 检查权限
            mode = 'do' if '/do' in self.request.path else 'update'
            self.check_task_auth(task, mode)
            r = self.check_task_lock(task, mode)
            if r is not True:
                return self.send_error_response(r)

            # 保存任务
            data = self.get_request_data()
            doubt = data.get('doubt', '').strip('\n')
            update = {'result.doubt': doubt, 'updated_time': datetime.now()}
            self.db.task.update_one({'_id': task['_id']}, {'$set': update})

            # 将数据结果同步到page中
            txt_html = data.get('txt_html', '').strip('\n')
            text = TextTool.html2txt(txt_html)
            self.db.page.update_one({'name': task['doc_id']}, {'$set': {'text': text, 'txt_html': txt_html}})

            if data.get('submit'):
                if mode == 'do':
                    self.finish_task(task)
                    self.add_op_log('submit_%s' % task_type, target_id=task_id)
                else:
                    self.release_temp_lock(task['doc_id'], shared_field='text')

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)


class TextEditApi(TaskHandler):
    URL = '/api/data/edit/text/@page_name'

    def post(self, page_name):
        """ 专家用户首先申请数据锁，然后可以修改数据。"""
        try:
            # 检查参数
            data = self.get_request_data()
            rules = [(v.not_empty, 'txt_html')]
            err = v.validate(data, rules)
            if err:
                return self.send_error_response(err)
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object)

            # 检查数据锁
            if not self.has_data_lock(page_name, 'text'):
                return self.send_error_response(errors.data_unauthorized)

            # 保存数据
            txt_html = data.get('txt_html') and json_decode(data['txt_html']).strip('\n')
            text = TextTool.html2txt(txt_html)
            r = self.db.page.update_one({'name': page_name}, {'$set': {'text': text, 'txt_html': txt_html}})
            if r.modified_count:
                self.add_op_log('save_edit_text', context=page_name, target_id=page['_id'])

            # 提交时，释放数据锁
            if data.get('submit'):
                self.release_temp_lock(page_name, shared_field='text')

            self.send_data_response()

        except DbError as e:
            self.send_db_error(e)
