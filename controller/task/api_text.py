#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from tornado.escape import url_escape
from controller.base import DbError
from controller import errors
from controller.task.base import TaskHandler
from operator import itemgetter


class CharProofDetailHandler(TaskHandler):
    URL = '/task/do/text_proof/@num/@task_id'

    def get(self, proof_num, name=''):
        """ 进入文字校对页面 """
        self.enter(self, 'text_proof.' + proof_num, name, ('proof', '文字校对'))

    @staticmethod
    def enter(self, task_type, name, stage):
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.render('_404.html')

            params = dict(page=page, name=page['name'], stage=stage, mismatch_lines=[])
            cmp_data = dict(segments=self.gen_segments(page['txt'], page['chars'], params))
            picked_user_id = self.get_obj_property(page, task_type + '.picked_user_id')
            self.render('text_proof.html',
                        origin_txt=re.split(r'[\n|]', page['txt'].strip()),
                        readonly=picked_user_id != self.current_user['_id'],
                        get_img=self.get_img, cmp_data=cmp_data, **params)
        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def gen_segments(txt, chars, params=None):
        def get_column_boxes():
            """得到当前栏中当前列的所有字框"""
            return [c1 for c1 in chars if c1.get('char_id', '').startswith('b%dc%dc' % (1 + blk_i, line_no))]

        def apply_span():
            """添加正常文本片段"""
            if items:
                segments.append(dict(block_no=1 + blk_i, line_no=line_no, type='same', ocr=items))

        assert '\n' not in txt
        segments = []
        chars_segment = 0
        # 处理每个栏的文本，相邻栏用两个空行隔开，数据库存储时是用竖号代替多行分隔符
        for blk_i, block_txt in enumerate(txt.replace('|', '\n').split('\n\n\n')):
            col_diff = 1
            block_txt = re.sub(r'\n{2}', '\n', block_txt, flags=re.M)  # 栏内的多余空行视为一个空行
            for col_i, column_txt in enumerate(block_txt.strip().split('\n')):  # 处理栏的每行文本
                column_txt = column_txt.strip().replace('\ufeff', '')  # 去掉特殊字符
                line_no = col_diff + col_i
                if not column_txt:  # 遇到空行则记录，空行不改变列号
                    segments.append(dict(block_no=1 + blk_i, line_no=line_no, type='emptyline', ocr=''))
                    continue
                while col_diff < 50 and not get_column_boxes():  # 跳过不存在的列号
                    col_diff += 1
                    line_no = col_diff + col_i

                boxes = get_column_boxes()
                chars_segment += len(boxes)
                column_strip = re.sub(r'\s', '', column_txt)
                if len(boxes) != len(column_strip):
                    if params and 'mismatch_lines' in params:
                        params['mismatch_lines'].append('b%dc%d' % (1 + blk_i, line_no))
                else:
                    for i, c in enumerate(boxes):
                        c['no'] = c.get('char_no') or c.get('no')
                        if not c['no'] and c.get('char_id'):  # b1c11c8
                            cid = c['char_id'][1:].split('c')
                            c['no'] = c['char_no'] = int(cid[2])
                            c['block_no'], c['line_no'] = int(cid[0]), int(cid[1])

                    for i, c in enumerate(sorted(boxes, key=itemgetter('no'))):
                        c['txt'] = column_strip[i]
                column_txt = [url_escape(c) for c in list(column_txt)]
                items = []
                for c in column_txt:
                    if len(c) > 9:  # utf8mb4大字符，例如 '%F0%AE%8D%8F'
                        apply_span()
                        items = []
                        segments.append(dict(block_no=1 + blk_i, line_no=line_no, type='variant', ocr=[c], cmp=''))
                    else:
                        items.append(c)
                apply_span()

        return segments


class CharReviewDetailHandler(TaskHandler):
    URL = '/task/do/text_review/@task_id'

    def get(self, name=''):
        """ 进入文字审定页面 """
        CharProofDetailHandler.enter(self, 'text_review', name, ('review', '文字审定'))


class SaveTextApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_request_data()
            assert re.match(r'^[A-Za-z0-9_]+$', data.get('name'))
            assert task_type in self.text_task_names

            page = self.db.page.find_one(dict(name=data['name']))
            if not page:
                return self.send_error_response(errors.no_object)

            status = self.get_obj_property(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.picked_user_id'
            page_user = self.get_obj_property(page, task_user)
            if page_user != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=page['name'])

            result = dict(name=data['name'])
            # self.change_box(result, page, data, task_type)
            if data.get('submit'):
                self.submit_task(result, data, page, task_type, task_user)

            self.send_data_response(result)
        except DbError as e:
            self.send_db_error(e)

    def submit_task(self, result, data, page, task_type, task_user):
        end_info = {
            task_type + '.status': self.STATUS_FINISHED,
            task_type + '.finished_time': datetime.now(),
            task_type + '.last_updated_time': datetime.now()
        }
        r = self.db.page.update_one({'name': page['name'], task_user: self.current_user['_id']}, {'$set': end_info})
        if r.modified_count:
            result['submitted'] = True
            self.add_op_log('submit_' + task_type, file_id=page['_id'], context=page['name'])

            # 激活后置任务，没有相邻后置任务则继续往后激活任务
            post_task = self.post_tasks().get(task_type)
            while post_task:
                next_status = post_task + '.status'
                status = self.get_obj_property(page, next_status)
                if status:
                    r = self.db.page.update_one({'name': page['name'], next_status: self.STATUS_PENDING},
                                                {'$set': {next_status: self.STATUS_OPENED}})
                    if r.modified_count:
                        self.add_op_log('resume_' + task_type, file_id=page['_id'], context=page['name'])
                        result['resume_next'] = post_task
                post_task = not status and self.post_tasks().get(post_task)

            task = self.pick_new_task(task_type)
            if task:
                self.add_op_log('jump_' + task_type, file_id=task['_id'], context=task['name'])
                result['jump'] = '/task/do/%s/%s' % (task_type.replace('.', '/'), task['name'])

    def pick_new_task(self, task_type):
        tasks = self.get_tasks_info_by_type(task_type, self.STATUS_OPENED, rand=True, sort=True)
        return tasks and tasks[0]


class SaveTextProofApi(SaveTextApi):
    URL = '/api/task/save/text_proof/@num'

    def post(self, num):
        """ 保存或提交文字校对任务 """
        self.save('text_proof.' + num)

    def pick_new_task(self, task_type):
        tasks = self.get_tasks_info_by_type('text_proof', self.STATUS_OPENED, rand=True, sort=True)
        picked = self.db.page.find({'$or': [
            {'text_proof.%d.picked_user_id' % i: self.current_user['_id']} for i in range(1, 4)
        ]}, {'name': 1})
        picked = [page['name'] for page in list(picked)]
        tasks = [t for t in tasks if t['name'] not in picked]
        return tasks and tasks[0]


class SaveTextReviewApi(SaveTextApi):
    URL = '/api/task/save/text_review'

    def post(self):
        """ 保存或提交文字审定任务 """
        self.save('text_review')
