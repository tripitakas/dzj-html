#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from operator import itemgetter
from tornado.web import UIModule
from tornado.escape import url_escape
from controller.task.base import TaskHandler
from controller.task.view_cut import CutBaseHandler
from controller.data.diff import Diff


class TextBaseHandler(TaskHandler):
    cmp_fields = {'text_proof_1': 'cmp1', 'text_proof_2': 'cmp2', 'text_proof_3': 'cmp3'}
    save_fields = {'text_proof_1': 'txt1_html', 'text_proof_2': 'txt2_html', 'text_proof_3': 'txt3_html',
                   'text_review': 'txt_html', 'text_hard': 'txt_html'}

    def get_segments(self, page, task_type):
        if 'proof' in task_type:
            base = page.get('ocr').replace('|', '\n')
            cmp = self.prop(page, self.cmp_fields.get(task_type))
            segments = Diff.diff(base, cmp or base, label=dict(cmp1='cmp'))[0]
        else:
            txt1 = self.get_txt_from_html(page.get('txt1_html'))
            txt2 = self.get_txt_from_html(page.get('txt2_html'))
            txt3 = self.get_txt_from_html(page.get('txt3_html'))
            segments = Diff.diff(txt1, txt2, txt3)[0]
        return segments

    def get_txts(self, page, task_type):
        if 'proof' in task_type:
            ocr = page.get('ocr').replace('|', '\n')
            cmp = self.prop(page, self.cmp_fields.get(task_type))
            txts = dict(ocr=ocr, cmp=cmp)
        else:
            txt1 = self.get_txt_from_html(page.get('txt1_html'))
            txt2 = self.get_txt_from_html(page.get('txt2_html'))
            txt3 = self.get_txt_from_html(page.get('txt3_html'))
            txts = dict(cmp1=txt1, cmp2=txt2, cmp3=txt3)
        return txts

    def get_labels(self, page, task_type):
        if 'proof' in task_type:
            labels = dict(base='OCR', cmp='比对本')
        else:
            labels = dict(base='校一', cmp1='校二')
            if len(self.prop(page, 'tasks.text_review.pre_tasks')) > 2:
                labels['cmp2'] = '校三'
        return labels

    @staticmethod
    def get_txt_from_html(html):
        lines = []
        regex = re.compile("<li.*?>.*?</li>", re.M | re.S)
        for line in regex.findall(html):
            if 'delete' not in line:
                txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|\s)', '', line, flags=re.M | re.S)
                lines.append(txt + '\n')
        return ''.join(lines)

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


class TextFindCmpHandler(TextBaseHandler):
    URL = ['/task/do/text_proof_@num/find_cmp/@page_name',
           '/task/update/text_proof_@num/find_cmp/@page_name']

    def get(self, num, page_name):
        """ 文字校对-选择比对本页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            mode = (re.findall('/(do|update)/', self.request.path) or ['view'])[0]
            task_type = 'text_proof_' + num
            readonly = not self.check_auth(mode, page, task_type)
            self.render(
                'task_text_find_cmp.html',
                task_type=task_type, page=page, num=num, ocr=page.get('ocr'),
                mode=mode, readonly=readonly, get_img=self.get_img,
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextProofHandler(TextBaseHandler):
    URL = ['/task/text_proof_@num/@page_name',
           '/task/do/text_proof_@num/@page_name',
           '/task/update/text_proof_@num/@page_name']

    def get(self, num, page_name):
        """ 文字校对页面 """

        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            # 如果find_cmp没有submit，则跳转find_cmp
            task_type = 'text_proof_' + num
            submitted_steps = self.prop(page, 'tasks.%s.submitted_steps' % task_type) or []
            mode = (re.findall('/(do|update)/', self.request.path) or ['view'])[0]
            if mode == 'do' and (not submitted_steps or 'find_cmp' not in submitted_steps):
                return self.redirect('/task/do/%s/find_cmp/%s' % (task_type, page_name))

            readonly = not self.check_auth(mode, page, task_type)
            doubt = self.prop(page, 'tasks.%s.doubt' % task_type)
            params = dict(mismatch_lines=[])
            layout = int(self.get_query_argument('layout', 0))
            CutBaseHandler.char_render(page, layout, **params)
            cmp_data = page.get(self.save_fields[task_type])
            if not cmp_data:
                segments = self.get_segments(page, task_type)
                cmp_data = self.check_segments(segments, page['chars'], params)
            self.render(
                'task_text_do.html',
                task_type=task_type, page=page, cmp_data=cmp_data, doubt=doubt, mode=mode, readonly=readonly,
                txts=self.get_txts(page, task_type), get_img=self.get_img, labels=self.get_labels(page, task_type),
                **params
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextReviewHandler(TextBaseHandler):
    URL = ['/task/text_review/@page_name',
           '/task/do/text_review/@page_name',
           '/task/update/text_review/@page_name',
           '/data/edit/text/@page_name']

    def get(self, page_name):
        """ 文字审定页面 """
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            task_type = 'text_review'
            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(mode, page, task_type)
            doubt = self.prop(page, 'tasks.%s.doubt' % task_type)
            proof_doubt = ''
            for i in range(1, 4):
                proof_doubt += self.prop(page, 'tasks.text_proof_%s.doubt' % i) or ''

            params = dict(mismatch_lines=[])
            layout = int(self.get_query_argument('layout', 0))
            CutBaseHandler.char_render(page, layout, **params)
            cmp_data = page.get(self.save_fields[task_type])
            if not cmp_data:
                segments = self.get_segments(page, task_type)
                cmp_data = self.check_segments(segments, page['chars'], params)

            self.render(
                'task_text_do.html',
                task_type=task_type, page=page, cmp_data=cmp_data, doubt=doubt, mode=mode, readonly=readonly,
                proof_doubt=proof_doubt, get_img=self.get_img, txts=self.get_txts(page, task_type),
                labels=self.get_labels(page, task_type),
                **params
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextHardHandler(TextBaseHandler):
    URL = ['/task/text_hard/@page_name',
           '/task/do/text_hard/@page_name',
           '/task/update/text_hard/@page_name']

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
            layout = int(self.get_query_argument('layout', 0))
            CutBaseHandler.char_render(page, layout, **params)
            cmp_data = page.get(self.save_fields[task_type])

            self.render(
                'task_text_do.html',
                task_type=task_type, page=page, cmp_data=cmp_data, doubt=doubt, mode=mode, readonly=readonly,
                txts=self.get_txts(page, task_type), get_img=self.get_img, labels=self.get_labels(page, task_type),
                **params
            )

        except Exception as e:
            self.send_db_error(e, render=True)


class TextArea(UIModule):
    """文字校对的文字区"""

    def render(self, segments, raw=False):
        cur_line_no = 0
        items = []
        lines = []
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
                items.append(item)
            item['block_no'] = blocks[-1]['block_no']

        cmp_names = dict(base='基准', cmp='外源', cmp1='校一', cmp2='校二', cmp3='校三')
        if raw:
            return dict(blocks=blocks, cmp_names=cmp_names)
        return self.render_string('task_text_area.html', blocks=blocks, cmp_names=cmp_names)
