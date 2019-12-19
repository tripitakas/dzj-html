#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
from tornado.web import UIModule
from bson.objectid import ObjectId
from controller import errors as errors
from controller.text.diff import Diff
from controller.cut.cuttool import CutTool
from controller.task.base import TaskHandler
from controller.text.texttool import TextTool


class TextProofHandler(TaskHandler, TextTool):
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
                return self.send_error_response(errors.no_object, message='没有找到页面%s' % task['doc_id'])

            has_auth, error = self.check_task_auth(task)
            if not has_auth:
                return self.send_error_response(error, message='%s (%s)' % (error[1], page['name']))
            mode = self.get_task_mode()
            readonly = 'view' == mode
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            if steps['current'] == 'select_compare_text':
                return self.select_compare_text(task, page, mode, steps, readonly, num)
            else:
                return self.proof(task, page, mode, steps, readonly)

        except Exception as error:
            return self.send_db_error(error)

    def select_compare_text(self, task, page, mode, steps, readonly, num):
        self.render(
            'task_text_compare.html', task_type=task['task_type'], task=task, page=page,
            mode=mode, readonly=readonly, num=num, steps=steps, ocr=page.get('ocr'),
            cmp=self.prop(task, 'result.cmp'), get_img=self.get_img,
        )

    def proof(self, task, page, mode, steps, readonly):
        """ 文字校对
        文本来源有多种情况，ocr可能会输出两份数据，比对本可能有一份数据。
        """
        doubt = self.prop(task, 'result.doubt')
        CutTool.char_render(page, int(self.get_query_argument('layout', 0)))

        # 获取比对来源的文本
        ocr = page.get('ocr') or ''
        ocr_col = page.get('ocr_col') or ''
        cmp = self.prop(task, 'result.cmp')
        texts = dict(base=re.sub(r'\|+', '\n', ocr), cmp1=ocr_col if ocr_col else cmp, cmp2=cmp if ocr_col else '')
        labels = dict(base='OCR', cmp1='OCR' if ocr_col else '比对本', cmp2='比对本' if ocr_col else '')

        # 检查是否已进行比对
        params = dict(mismatch_lines=[])
        cmp_data = self.prop(task, 'result.txt_html')
        re_compare = self.get_query_argument('re_compare', 'false')
        if not cmp_data or re_compare == 'true':
            segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
            cmp_data = self.check_segments(segments, page['chars'], params)

        self.render(
            'task_text_do.html', task_type=task['task_type'], task=task, page=page, mode=mode, readonly=readonly,
            texts=texts, labels=labels, cmp_data=cmp_data, doubt=doubt, pre_doubt='',
            steps=steps, get_img=self.get_img, **params
        )


class TextReviewHandler(TaskHandler, TextTool):
    URL = ['/task/text_review/@task_id',
           '/task/do/text_review/@task_id',
           '/task/update/text_review/@task_id']

    @staticmethod
    def get_cmp_data(self, doc_id, page):
        """ 如果有文字校对任务，则从文字校对中获取比对文本。如果没有，则依次从text/ocr中获取比对文本"""
        has_proof, doubt, proofs = False, '', ['', '', '']
        for i in [1, 2, 3]:
            condition = {'task_type': 'text_proof_%s' % i, 'doc_id': doc_id, 'status': self.STATUS_FINISHED}
            proof_task = self.db.task.find_one(condition)
            if proof_task:
                has_proof = True
                doubt += self.prop(proof_task, 'result.doubt') or ''
                proofs[i - 1] = self.html2txt(self.prop(proof_task, 'result.txt_html'))
        if has_proof:
            texts = dict(base=proofs[0], cmp1=proofs[1], cmp2=proofs[2])
            labels = dict(base='校一', cmp1='校一', cmp2='校三')
        else:
            txt = page.get('text') or page.get('ocr') or ''
            texts = dict(base=re.sub(r'\|+', '\n', txt), cmp1='', cmp2='')
            labels = dict(base='文本一', cmp1='', cmp2='')
        return doubt, texts, labels

    def get(self, task_id):
        """ 文字审定页面"""
        try:
            task_type = 'text_review'
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({'name': task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, message='没有找到页面%s' % task['doc_id'])

            # 检查任务权限及数据锁
            has_auth, error = self.check_task_auth(task)
            if not has_auth:
                return self.send_error_response(error, message='%s (%s)' % (error[1], page['name']))
            has_lock = self.check_task_lock(task)[0]

            mode = self.get_task_mode()
            params = dict(mismatch_lines=[])
            CutTool.char_render(page, int(self.get_query_argument('layout', 0)), **params)
            review_doubt = self.prop(task, 'result.doubt')
            proof_doubt, texts, labels = self.get_cmp_data(self, task['doc_id'], page)
            cmp_data = self.prop(page, 'txt_html')
            if not cmp_data:
                segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
                cmp_data = self.check_segments(segments, page['chars'], params)

            self.render(
                'task_text_do.html', task_type=task_type, task=task, page=page, mode=mode,
                readonly=not has_lock, texts=texts, labels=labels, cmp_data=cmp_data,
                doubt=review_doubt, pre_doubt=proof_doubt, get_img=self.get_img,
                steps=dict(is_first=True, is_last=True), **params
            )

        except Exception as error:
            return self.send_db_error(error)


class TextHardHandler(TextReviewHandler):
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
                return self.send_error_response(errors.no_object)

            # 检查任务权限及数据锁
            has_auth, error = self.check_task_auth(task)
            if not has_auth:
                return self.send_error_response(error, message='%s (%s)' % (error[1], page['name']))
            has_lock, error = self.check_task_lock(task)

            mode = self.get_task_mode()
            proof_doubt, texts = self.get_cmp_data(self, task['doc_id'])
            review_task = self.db.task.find_one({'_id': self.prop(task, 'input.review_task')})
            review_doubt = self.prop(review_task, 'result.doubt') if review_task else None
            hard_doubt = self.prop(task, 'result.doubt')
            cmp_data = self.prop(page, 'txt_html')
            labels = dict(base='校一', cmp1='校一', cmp2='校三')
            kwargs = dict(texts=texts, labels=labels, steps=dict(is_first=True, is_last=True))
            self.render(
                'task_text_do.html', task_type=task_type, task=task, page=page, mode=mode,
                readonly=not has_lock, cmp_data=cmp_data, doubt=hard_doubt, pre_doubt=review_doubt,
                get_img=self.get_img, **kwargs
            )

        except Exception as error:
            return self.send_db_error(error)


class TextEditHandler(TaskHandler, TextTool):
    URL = '/data/edit/text/@page_name'

    def get(self, page_name):
        """ 文字修改页面 """

        try:
            page = self.db.page.find_one({'name': page_name})
            if not page:
                return self.send_error_response(errors.no_object)

            has_lock = self.get_data_lock(page_name, 'text') is True
            cmp_data = self.prop(page, 'txt_html') or ''
            if not cmp_data and self.prop(page, 'text'):
                segments = Diff.diff(self.prop(page, 'text').replace('|', '\n'))[0]
                cmp_data = self.check_segments(segments, page['chars'], dict(mismatch_lines=[]))

            kwargs = dict(task_type='', task={}, texts={}, labels={}, doubt='', pre_doubt='',
                          steps=dict(is_first=True, is_last=True))
            self.render(
                'task_text_do.html', page=page, mode='edit', readonly=not has_lock, cmp_data=cmp_data,
                get_img=self.get_img, **kwargs

            )

        except Exception as error:
            return self.send_db_error(error)


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
