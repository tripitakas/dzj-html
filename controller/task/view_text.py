#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from operator import itemgetter
from tornado.web import UIModule
from controller.diff import Diff
from tornado.escape import url_escape
from controller.task.base import TaskHandler
from controller.task.view_cut import CutBaseHandler


class TextBaseHandler(TaskHandler):
    cmp_fields = {
        'text_proof_1': 'cmp1',
        'text_proof_2': 'cmp2',
        'text_proof_3': 'cmp3',
    }

    def get_segments(self, task_type, page):
        if 'proof' in task_type:
            base = page.get('ocr').replace('|', '\n')
            cmp = self.prop(page, self.cmp_fields.get(task_type))
            segments = Diff.diff(base, cmp or base, label=dict(cmp1='cmp'))[0]
            txts = dict(base=base, cmp=cmp)
        elif 'review' in task_type:
            # review时应对txt1/txt2/txt/3比对，暂时由ocr/cmp1/cmp2替代
            base = page.get('ocr').replace('|', '\n')
            cmp1 = self.prop(page, self.cmp_fields.get('text_proof_1'))
            cmp2 = list(cmp1 or base)
            # 对cmp2进行变换处理
            del cmp2[4]
            del cmp2[-4]
            mid = int(len(cmp2) / 2)
            cmp2.insert(mid, '新增')
            cmp2[mid - 4:mid - 2] = '替换'
            cmp2[mid + 2:mid + 4] = '修改'

            segments = Diff.diff(base, cmp1 or base, ''.join(cmp2))[0]
            txts = dict(base=base, cmp1=cmp1, cmp2=cmp2)

        return segments, txts

    def enter(self, task_type, page_name):
        assert task_type in ['text_proof_1', 'text_proof_2', 'text_proof_3', 'text_review']
        try:
            page = self.db.page.find_one(dict(name=page_name))
            if not page:
                return self.render('_404.html')

            mode = (re.findall('/(do|update|edit)/', self.request.path) or ['view'])[0]
            readonly = not self.check_auth(mode, page, task_type)
            params = dict(name=page_name, mismatch_lines=[], columns=page['columns'])
            layout = int(self.get_query_argument('layout', 0))
            CutBaseHandler.char_render(page, layout, **params)
            segments, txts = self.get_segments(task_type, page)
            cmp_data = self.check_segments(segments, page['chars'], params)
            self.render(
                'task_text_proof.html',
                task_type=task_type, page=page, cmp_data=cmp_data, mode=mode, readonly=readonly,
                origin_txt=re.split(r'[\n|]', txts['base'].strip()),
                cmp_txt=re.split(r'[\n|]', (txts.get('cmp', '')).strip()),
                get_img=self.get_img,
                **params
            )

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


class TextProofHandler(TextBaseHandler):
    URL = ['/task/text_proof_@num/@page_name',
           '/task/do/text_proof_@num/@page_name',
           '/task/update/text_proof_@num/@page_name']

    def get(self, num, page_name):
        """ 进入文字校对页面 """
        self.enter('text_proof_' + num, page_name)


class TextReviewHandler(TextBaseHandler):
    URL = ['/task/text_review/@page_name',
           '/task/do/text_review/@page_name',
           '/task/update/text_review/@page_name',
           '/data/edit/text/@page_name']

    def get(self, page_name):
        """ 进入文字审定页面 """
        self.enter('text_review', page_name)
