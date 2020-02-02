#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import logging
from bson import json_util
from bson.objectid import ObjectId
from datetime import datetime
from tornado.escape import json_decode
from controller import errors as e
from controller.base import DbError
from controller import validate as v
from controller.page.diff import Diff
from controller.page.base import PageHandler
from controller.task.base import TaskHandler
from controller.page.submit import SubmitDataTaskHandler
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
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)
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
            return self.send_data_response()

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
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            has_lock, error = self.check_data_lock(page_name, 'box')
            if not has_lock:
                return self.send_error_response(error)

            update = dict()
            data['boxes'] = json_decode(data['boxes']) if isinstance(data['boxes'], str) else data['boxes']
            if data['step'] == 'orders':
                assert data.get('chars_col')
                update['chars'] = self.reorder_chars(data['chars_col'], self.page['chars'], page=self.page)
            else:
                update[data['step']] = self.sort_boxes(data['boxes'], data['step'], page=self.page)
            self.db.page.update_one({'name': self.page_name}, {'$set': update})
            self.add_op_log('edit_box', context=page_name, target_id=self.page['_id'])

            if data.get('submit'):
                self.release_temp_lock(page_name, 'box', self.current_user)

            return self.send_data_response()

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
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)

            if data['step'] == 'select':
                return self.save_select(data)
            else:
                return self.save_proof(data)

        except DbError as error:
            return self.send_db_error(error)

    def save_select(self, data):
        update = {'result.cmp': data['cmp'].strip('\n'), 'updated_time': datetime.now()}
        if data.get('submit'):
            update.update({'steps.submitted': self.get_submitted(data['step'])})
        self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
        self.add_op_log('save_%s' % self.task_type, context=self.task['doc_id'], target_id=self.task['_id'])

    def save_proof(self, data):
        doubt = data.get('doubt', '').strip('\n')
        txt_html = data.get('txt_html', '').strip('\n')
        update = {'result.doubt': doubt, 'result.txt_html': txt_html, 'updated_time': datetime.now()}
        self.db.task.update_one({'_id': self.task['_id']}, {'$set': update})
        self.add_op_log('save_%s' % self.task_type, context=self.task['doc_id'], target_id=self.task['_id'])
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
        self.add_op_log('publish_text_hard', context=str(review_task['_id']), target_id=r.inserted_id)
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
            errs = v.validate(data, rules)
            if errs:
                return self.send_error_response(errs)
            # 更新page
            txt_html = data.get('txt_html', '').strip('\n')
            self.update_page_txt_html(txt_html)
            if data.get('submit'):
                self.release_temp_lock(page_name, 'text', self.current_user)
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
            errs = v.validate(data, [(v.not_empty, 'cmp_page_code', 'neighbor')])
            if errs:
                return self.send_error_response(errs)

            neighbor = find_neighbor(data.get('cmp_page_code'), data.get('neighbor'))
            if neighbor:
                txt = Diff.pre_cmp(''.join(neighbor['_source']['origin']))
                self.send_data_response(dict(txt=txt, code=neighbor['_source']['page_code']))
            else:
                self.send_error_response(e.no_object, message='没有更多内容')

        except DbError as error:
            return self.send_db_error(error)


class FetchDataTasksApi(TaskHandler):
    URL = '/api/task/fetch_many/@data_task'

    def post(self, data_task):
        """ 批量领取数据任务"""

        def get_tasks():
            # ocr_box、ocr_text时，锁定box，以免修改
            condition = {'name': {'$in': [t['doc_id'] for t in tasks]}}
            if data_task in ['ocr_box', 'ocr_text']:
                self.db.page.update_many(condition, {'$set': {'lock.box': {
                    'is_temp': False,
                    'lock_type': dict(tasks=data_task),
                    'locked_by': self.current_user['name'],
                    'locked_user_id': self.current_user['_id'],
                    'locked_time': datetime.now()
                }}})
            # ocr_box、ocr_text时，把layout/blocks/columns/chars等参数传过去
            if data_task in ['ocr_box', 'ocr_text']:
                params = self.db.page.find(condition)
                fields = ['layout'] if data_task == 'ocr_box' else ['layout', 'blocks', 'columns', 'chars']
                params = {p['name']: {k: p.get(k) for k in fields} for p in params}
                for t in tasks:
                    t['input'] = params.get(t['doc_id'])
                    if not t['input']:
                        logging.warning('page %s not found' % t['doc_id'])

            return [dict(task_id=str(t['_id']), priority=t.get('priority'), page_name=t.get('doc_id'),
                         input=t.get('input')) for t in tasks]

        try:
            data = self.get_request_data()
            size = int(data.get('size') or 1)
            condition = {'task_type': data_task, 'status': self.STATUS_PUBLISHED}
            tasks = list(self.db.task.find(condition).limit(size))
            if not tasks:
                self.send_data_response(dict(tasks=None))

            # 批量获取任务
            condition.update({'_id': {'$in': [t['_id'] for t in tasks]}})
            r = self.db.task.update_many(condition, {'$set': dict(
                status=self.STATUS_FETCHED, picked_time=datetime.now(), updated_time=datetime.now(),
                picked_user_id=self.current_user['_id'], picked_by=self.current_user['name']
            )})
            if r.matched_count:
                logging.info('%d %s tasks fetched' % (r.matched_count, data_task))
                self.send_data_response(dict(tasks=get_tasks()))

        except DbError as error:
            return self.send_db_error(error)


class ConfirmFetchDataTasksApi(TaskHandler):
    URL = '/api/task/confirm_fetch/@data_task'

    def post(self, data_task):
        """ 确认批量领取任务成功 """

        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            task_ids = [ObjectId(t['task_id']) for t in data['tasks']]
            if task_ids:
                self.db.task.update_many({'_id': {'$in': task_ids}}, {'$set': {'status': self.STATUS_PICKED}})
                self.send_data_response()
            else:
                self.send_error_response(e.no_object)

        except DbError as error:
            return self.send_db_error(error)


class SubmitDataTasksApi(SubmitDataTaskHandler):
    URL = '/api/task/submit/@data_task'

    def post(self, task_type):
        """ 批量提交数据任务。提交参数为tasks，格式如下：
        [{'task_type': '', 'ocr_task_id':'', 'task_id':'', 'page_name':'', 'status':'success', 'result':{}},
         {'task_type': '', 'ocr_task_id':'','task_id':'', 'page_name':'', 'status':'failed', 'message':''},
        ]
        其中，ocr_task_id是远程任务id，task_id是本地任务id，status为success/failed，
        result是成功时的数据，message为失败时的错误信息。
        """
        try:
            data = self.get_request_data()
            rules = [(v.not_empty, 'tasks')]
            err = v.validate(data, rules)
            if err:
                self.send_error_response(err)

            tasks = []
            for task in data['tasks']:
                r = self.submit_one(task)
                message = '' if r is True else r
                status = 'success' if r is True else 'failed'
                tasks.append(dict(ocr_task_id=task['ocr_task_id'], task_id=task['task_id'], status=status,
                                  page_name=task.get('page_name'), message=message))
            self.send_data_response(dict(tasks=tasks))

        except DbError as error:
            return self.send_db_error(error)
