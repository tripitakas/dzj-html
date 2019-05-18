#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from datetime import datetime
from tornado.escape import url_escape, json_decode
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
            p = self.db.page.find_one(dict(name=name))
            if not p:
                return self.render('_404.html')

            for c in p['chars']:
                c.pop('txt', 0)
            params = dict(page=p, name=name, stage=stage, mismatch_lines=[], columns=p['columns'])
            cmp_data = dict(segments=CharProofDetailHandler.gen_segments(p['txt'], p['chars'], params))
            picked_user_id = self.get_obj_property(p, task_type + '.picked_user_id')
            self.render('text_proof.html', task_type=task_type,
                        origin_txt=re.split(r'[\n|]', p['txt'].strip()),
                        readonly=picked_user_id != self.current_user['_id'],
                        get_img=self.get_img, cmp_data=cmp_data, **params)
        except Exception as e:
            self.send_db_error(e, render=True)

    @staticmethod
    def normalize_boxes(page):
        for c in page.get('chars', []):
            cid = c.get('char_id', '')[1:].split('c')
            if len(cid) == 3:
                c['no'] = c['char_no'] = int(cid[2])
                c['block_no'], c['line_no'] = int(cid[0]), int(cid[1])
            else:
                c['no'] = c['char_no'] = c.get('char_no') or c.get('no', 0)
                c['block_no'] = c.get('block_no', 0)
                c['line_no'] = c.get('line_no', 0)
                c['char_id'] = 'b%dc%dc%d' % (c.get('block_no'), c.get('line_no'), c.get('no'))
        for c in page.get('columns', []):
            c.pop('char_id', 0)
            c.pop('char_no', 0)

    @staticmethod
    def gen_segments(txt, chars, params=None):
        def get_column_boxes():
            """得到当前栏中当前列的所有字框"""
            return [c1 for c1 in chars if c1.get('char_id', '').startswith('b%dc%dc' % (1 + blk_i, line_no))]

        segments = []
        chars_segment = 0
        params = params or {}
        CharProofDetailHandler.normalize_boxes(dict(chars=chars, columns=params.get('columns') or []))

        # 处理每个栏的文本，相邻栏用两个空行隔开，数据库存储时是用竖号代替多行分隔符
        txt = re.sub(r'\n+$', '', txt.replace('|', '\n'))
        for blk_i, block_txt in enumerate(txt.split('\n\n\n')):
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
                CharProofDetailHandler.fill_segments(blk_i + 1, line_no, column_txt, params, boxes, segments)

        return segments

    @staticmethod
    def fill_segments(blk_no, line_no, column_txt, params, boxes, segments):
        def apply_span():
            if items:
                segments.append(dict(block_no=blk_no, line_no=line_no, type='same', ocr=items))

        column_strip = re.sub(r'\s', '', column_txt)
        if len(boxes) != len(column_strip) and 'mismatch_lines' in params:
            params['mismatch_lines'].append('b%dc%d' % (blk_no, line_no))

        for i, c in enumerate(sorted(boxes, key=itemgetter('no'))):
            c['txt'] = column_strip[i] if i < len(column_strip) else '?'

        column_txt = [url_escape(c) for c in list(column_txt)]
        items = []
        for c in column_txt:
            if len(c) > 9:  # utf8mb4大字符，例如 '%F0%AE%8D%8F'
                apply_span()
                items = []
                segments.append(dict(block_no=blk_no, line_no=line_no, type='variant', ocr=[c], cmp=''))
            else:
                items.append(c)
        apply_span()


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

            name = data['name']
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)

            status = self.get_obj_property(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=self.task_statuses.get(status))

            task_user = task_type + '.picked_user_id'
            page_user = self.get_obj_property(page, task_user)
            if page_user != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=name)

            result = dict(name=name)
            txt = data.get('txt') and re.sub(r'\|+$', '', json_decode(data['txt']).replace('\n', '|'))
            if txt and txt != page['txt']:
                assert isinstance(txt, str)
                page['txt'] = txt
                result['changed'] = True
                self.db.page.update_one(dict(name=name), {'$set': {
                    'txt': txt, '%s.last_updated_time' % task_type: datetime.now()
                }})
                self.add_op_log('save_' + task_type, file_id=page['_id'], context=name)

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
