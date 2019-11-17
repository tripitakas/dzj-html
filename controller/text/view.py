#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from tornado.web import UIModule
from bson.objectid import ObjectId
import controller.errors as errors
from controller.text.diff import Diff
from controller.cut.view import CutHandler
from controller.task.base import TaskHandler
from .pack import TextPack


class TextProofHandler(TaskHandler, TextPack):
    URL = ['/task/text_proof_@num/@task_id',
           '/task/do/text_proof_@num/@task_id',
           '/task/update/text_proof_@num/@task_id']

    def get(self, num, task_id):
        """ 文字校对页面 """
        try:
            task_type = 'text_proof_' + num
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({'name': task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 检查任务权限
            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            self.check_task_auth(task, mode)

            readonly = 'view' == mode
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            if steps['current'] == 'select_compare_text':
                return self.select_compare_text(task, page, mode, steps, readonly, num)
            else:
                return self.proof(task, page, mode, steps, readonly)
        except Exception as e:
            return self.send_db_error(e, render=True)

    def select_compare_text(self, task, page, mode, steps, readonly, num):
        ocr = page.get('ocr')
        ocr = '|'.join(ocr) if isinstance(ocr, list) else ocr
        self.render(
            'task_text_select_compare.html',
            task_type=task['task_type'], task=task, page=page, mode=mode, readonly=readonly, num=num,
            steps=steps, ocr=ocr, cmp=self.prop(task, 'result.cmp'), get_img=self.get_img,
        )

    def proof(self, task, page, mode, steps, readonly):
        doubt = self.prop(task, 'result.doubt')
        params = dict(mismatch_lines=[])
        CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **params)
        ocr = re.sub(r'\|', '\n', page.get('ocr')) or ''
        cmp = self.prop(task, 'result.cmp')
        texts = dict(base=ocr, cmp1=cmp, cmp2='')
        cmp_data = self.prop(task, 'result.txt_html')
        re_compare = self.get_query_argument('re_compare', 'false')
        if not cmp_data or re_compare == 'true':
            segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
            cmp_data = self.check_segments(segments, page['chars'], params)
        self.render(
            'task_text_do.html', task_type=task['task_type'], task=task, page=page, mode=mode, readonly=readonly,
            texts=texts, cmp_data=cmp_data, doubt=doubt, steps=steps, get_img=self.get_img, **params
        )


class TextReviewHandler(TaskHandler, TextPack):
    URL = ['/task/text_review/@task_id',
           '/task/do/text_review/@task_id',
           '/task/update/text_review/@task_id']

    def get(self, task_id):
        """ 文字审定页面 """

        def get_proof_meta():
            _doubt, _texts = '', ['', '', '']
            for i in [1, 2, 3]:
                condition = {'task_type': 'text_proof_%s' % i, 'doc_id': task['doc_id'],
                             'status': self.STATUS_FINISHED}
                proof_task = self.db.task.find_one(condition)
                if proof_task:
                    _doubt += self.prop(proof_task, 'result.doubt') or ''
                    _texts[i - 1] = self.html2txt(TaskHandler.prop(proof_task, 'result.txt_html'))
            return _doubt, dict(base=_texts[0], cmp1=_texts[1], cmp2=_texts[2])

        try:
            task_type = 'text_review'
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({'name': task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 检查任务权限及数据锁
            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            self.check_task_auth(task, mode)
            has_lock = self.check_task_lock(task, mode) is True

            params = dict(mismatch_lines=[])
            layout = int(self.get_query_argument('layout', 0))
            CutHandler.char_render(page, layout, **params)
            review_doubt = self.prop(task, 'result.doubt')
            proof_doubt, texts = get_proof_meta()
            cmp_data = self.prop(page, 'txt_html')
            if not cmp_data:
                segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
                cmp_data = self.check_segments(segments, page['chars'], params)

            self.render(
                'task_text_do.html', task_type=task_type, task=task, page=page, mode=mode, readonly=not has_lock,
                texts=texts, cmp_data=cmp_data, doubt=review_doubt, proof_doubt=proof_doubt,
                get_img=self.get_img, steps=dict(is_first=True, is_last=True), **params
            )

        except Exception as e:
            return self.send_db_error(e, render=True)


class TextHardHandler(TaskHandler, TextPack):
    URL = ['/task/text_hard/@task_id',
           '/task/do/text_hard/@task_id',
           '/task/update/text_hard/@task_id']

    def get(self, task_id):
        """ 难字审定页面 """
        try:
            task_type = 'text_hard'
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({'name': task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 检查任务权限及数据锁
            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            self.check_task_auth(task, mode)
            has_lock = self.check_task_lock(task, mode) is True

            hard = self.prop(task, 'result.hard')
            cmp_data = self.prop(page, 'txt_html')

            # 缺省参数
            args = dict(texts={}, steps=dict(is_first=True, is_last=True))
            self.render(
                'task_text_do.html', task_type=task_type, task=task, page=page, mode=mode, readonly=not has_lock,
                cmp_data=cmp_data, doubt=hard, get_img=self.get_img, **args
            )

        except Exception as e:
            return self.send_db_error(e, render=True)


class TextEditHandler(TaskHandler, TextPack):
    URL = '/data/edit/text/@page_name'

    def get(self, page_name):
        """ 文字修改页面 """

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            # 获取数据锁
            has_lock = self.get_data_lock(page_name, 'text') is True
            cmp_data = self.prop(page, 'txt_html') or ''

            # 缺省参数
            args = dict(task_type='', task=dict(), texts={}, doubt='', steps=dict(is_first=True, is_last=True))
            self.render(
                'task_text_do.html', page=page, mode='edit', readonly=not has_lock, cmp_data=cmp_data,
                get_img=self.get_img, **args

            )

        except Exception as e:
            return self.send_db_error(e, render=True)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, segments, raw=False):
        cur_line_no, items, lines = 0, [], []
        blocks = [dict(block_no=1, lines=lines)]
        for item in segments:
            if 'block_no' in item and item['block_no'] != blocks[-1]['block_no']:
                lines = []
                blocks.append(dict(block_no=blocks[-1]['block_no'] + 1, lines=lines))
            if item['line_no'] != cur_line_no:
                cur_line_no = item['line_no']
                items = [item]
                lines.append(dict(line_no=cur_line_no, items=items))
                item['offset'] = 0
            elif items:
                item['offset'] = items[-1]['offset'] + len(items[-1]['base'])
                if item['base'] != '\n':
                    items.append(item)
            item['block_no'] = blocks[-1]['block_no']

        return dict(blocks=blocks) if raw else self.render_string('task_text_area.html', blocks=blocks)
