#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from operator import itemgetter
from tornado.web import UIModule
import controller.errors as errors
from bson.objectid import ObjectId
from tornado.escape import url_escape
from controller.data.diff import Diff
from controller.cut.view import CutHandler
from controller.task.base import TaskHandler


class TextTools(object):
    @classmethod
    def html2txt(cls, html):
        lines = []
        regex = re.compile("<li.*?>.*?</li>", re.M | re.S)
        for line in regex.findall(html or ''):
            if 'delete' not in line:
                txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|\s)', '', line, flags=re.M | re.S)
                lines.append(txt + '\n')
        return ''.join(lines).rstrip('\n')

    @staticmethod
    def check_segments(segments, chars, params=None):
        """ 检查segments """
        params = params or {}

        # 按列对字框分组，提取列号
        TextProofHandler.normalize_boxes(dict(chars=chars, columns=params.get('columns') or []))
        column_ids = sorted(list(set((c['block_no'], c['line_no']) for c in chars)))

        # 然后逐行对应并分配栏列号，匹配时不做文字比较
        # 输入参数txt与字框的OCR文字通常是顺序一致的，假定文字的行分布与字框的列分布一致
        line_no = 0
        matched_boxes = []
        for seg in segments:
            if seg['line_no'] > len(column_ids):
                break
            if line_no != seg['line_no']:
                line_no = seg['line_no']
                boxes = [c for c in chars if (c['block_no'], c['line_no']) == column_ids[line_no - 1]]
                column_txt = ''.join(s.get('base', '') for s in segments if s['line_no'] == line_no)
                column_strip = re.sub(r'\s', '', column_txt)

                if len(boxes) != len(column_strip) and 'mismatch_lines' in params:
                    params['mismatch_lines'].append('b%dc%d' % (boxes[0]['block_no'], boxes[0]['line_no']))
                for i, c in enumerate(sorted(boxes, key=itemgetter('no'))):
                    c['txt'] = column_strip[i] if i < len(column_strip) else '?'
                    matched_boxes.append(c)
            seg['txt_line_no'] = seg.get('txt_line_no', seg['line_no'])
            seg['line_no'] = boxes[0]['line_no']
            seg['block_no'] = boxes[0]['block_no']

        for c in chars:
            if c not in matched_boxes:
                c.pop('txt', 0)

        return segments

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


class TextProofHandler(TaskHandler, TextTools):
    URL = ['/task/text_proof_@num/@task_id',
           '/task/do/text_proof_@num/@task_id',
           '/task/update/text_proof_@num/@task_id']

    default_steps = dict(select_compare_text='选择比对文本', proof='文字校对')

    def get(self, num, task_id):
        """ 文字校对页面 """
        try:
            task_type = 'text_proof_' + num
            task = self.db.task.find_one(dict(task_type=task_type, _id=ObjectId(task_id)))
            if not task:
                return self.render('_404.html')
            page = self.db.page.find_one({task['id_name']: task['doc_id']})
            if not page:
                return self.send_error_response(errors.no_object, render=True)

            mode = (re.findall('(do|update)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(task, mode)
            steps = self.init_steps(task, mode, self.get_query_argument('step', ''))
            if steps['current'] == 'select_compare_text':
                self.select_compare_text(task, page, mode, steps, readonly, num)
            else:
                self.proof(task, page, mode, steps, readonly)
        except Exception as e:
            self.send_db_error(e, render=True)

    def select_compare_text(self, task, page, mode, steps, readonly, num):
        self.render(
            'task_text_select_compare.html',
            task_type=task['task_type'], task_id=task['_id'], page=page, mode=mode, readonly=readonly, num=num,
            steps=steps, ocr=page.get('ocr'), cmp=self.prop(task, 'result.cmp'), get_img=self.get_img,
        )

    def proof(self, task, page, mode, steps, readonly):
        doubt = self.prop(task, 'result.doubt')
        params = dict(mismatch_lines=[])
        CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **params)
        ocr = re.sub(r'\|+', '\n', page.get('ocr')) or ''
        cmp1 = self.prop(task, 'result.cmp')
        texts = dict(base=ocr, cmp1=cmp1, cmp2='')
        cmp_data = self.prop(task, 'result.txt_html')
        if not cmp_data:
            segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
            cmp_data = self.check_segments(segments, page['chars'], params)
        self.render(
            'task_text_do.html', task_type=task['task_type'], page=page, mode=mode, readonly=readonly,
            texts=texts, cmp_data=cmp_data, doubt=doubt, steps=steps, get_img=self.get_img, **params
        )


class TextReviewHandler(TaskHandler, TextTools):
    URL = ['/task/text_review/@task_id',
           '/task/do/text_review/@task_id',
           '/task/update/text_review/@task_id',
           '/data/text_edit/@task_id']

    def get(self, page_name):
        """ 文字审定页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            task_type = 'text_review'
            mode = (re.findall('(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(mode, page, task_type)
            doubt = self.prop(page, 'tasks.%s.doubt' % task_type)
            proof_doubt = ''
            for i in range(1, 4):
                proof_doubt += self.prop(page, 'tasks.text_proof_%s.doubt' % i) or ''

            params = dict(mismatch_lines=[])
            layout = int(self.get_query_argument('layout', 0))
            CutHandler.char_render(page, layout, **params)
            base = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_1.txt_html'))
            cmp1 = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_2.txt_html'))
            cmp2 = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_3.txt_html'))
            texts = dict(base=base, cmp1=cmp1, cmp2=cmp2)
            cmp_data = self.prop(page, 'txt_html')
            if not cmp_data:
                segments = Diff.diff(texts['base'], texts['cmp1'], texts['cmp2'])[0]
                cmp_data = self.check_segments(segments, page['chars'], params)

            self.render(
                'task_text_do.html', task_type=task_type, page=page, mode=mode, readonly=readonly,
                texts=texts, cmp_data=cmp_data, doubt=doubt, proof_doubt=proof_doubt, get_img=self.get_img,
                steps=dict(is_first=True, is_last=True), **params
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextHardHandler(TaskHandler, TextTools):
    URL = ['/task/text_hard/@task_id',
           '/task/do/text_hard/@task_id',
           '/task/update/text_hard/@task_id']

    def get(self, page_name):
        """ 难字审定页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            task_type = 'text_hard'
            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(mode, page, task_type)
            doubt = self.prop(page, 'tasks.text_review.doubt')
            params = dict(mismatch_lines=[])
            CutHandler.char_render(page, int(self.get_query_argument('layout', 0)), **params)
            cmp_data = self.prop(page, 'txt_html')
            base = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_1.txt_html'))
            cmp1 = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_2.txt_html'))
            cmp2 = self.html2txt(TaskHandler.prop(page, 'tasks.text_proof_3.txt_html'))
            texts = dict(base=base, cmp1=cmp1, cmp2=cmp2)
            self.render(
                'task_text_do.html', task_type=task_type, page=page, mode=mode, readonly=readonly,
                texts=texts, cmp_data=cmp_data, doubt=doubt, get_img=self.get_img,
                steps=dict(is_first=True, is_last=True), **params
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, segments, raw=False):
        cur_line_no, items, lines = 0, [], []
        blocks = [dict(block_no=1, lines=lines)]
        for item in segments:
            if isinstance(item.get('ocr'), list):
                item['unicode'] = item['ocr']
                item['ocr'] = ''.join(c if re.match('^[A-Za-z0-9?*]$', c) else url_escape(c) if len(c) > 2 else ' '
                                      for c in item['ocr'])

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
