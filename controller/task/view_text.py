#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2019/5/13
"""
import re
from tornado.web import UIModule
from controller import errors
from operator import itemgetter
from controller.diff import Diff
from controller.task.base import TaskHandler
from tornado.escape import url_escape


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
        return self.render_string('text_proof_area.html', blocks=blocks, cmp_names=cmp_names)


class TextProofHandler(TaskHandler):
    URL = ['/task/text_proof.@num/@task_id', '/task/do/text_proof.@num/@task_id']

    def get(self, proof_num, name=''):
        """ 进入文字校对页面 """
        readonly = True if 'do' not in self.URL else False
        self.lock_enter(self, 'text_proof.' + proof_num, name, ('proof', '文字校对'), readonly)

    @staticmethod
    def lock_enter(self, task_type, name, stage, readonly):
        def handle_response(body):
            try:
                if not body.get('name') and not readonly:  # 锁定失败
                    return self.send_error_response(errors.task_locked, render=True, reason=name)

                TextProofHandler.enter(self, task_type, name, stage, readonly)
            except Exception as e:
                self.send_db_error(e, render=True)

        if readonly:
            handle_response({})
        else:
            from_url = self.get_query_argument('from', None)
            pick_from = '?from=' + from_url if from_url else ''
            self.call_back_api('/api/task/pick/{0}/{1}{2}'.format(task_type, name, pick_from), handle_response)

    @staticmethod
    def enter(self, task_type, name, stage, readonly=False):
        try:
            p = self.db.page.find_one(dict(name=name))
            if not p:
                return self.render('_404.html')

            params = dict(page=p, name=name, stage=stage, mismatch_lines=[], columns=p['columns'])
            txt = p.get('ocr', p.get('txt')).replace('|', '\n')
            cmp = self.get_obj_property(p, task_type + '.cmp')
            params['label'] = dict(cmp1='cmp')
            cmp_data = TextProofHandler.gen_segments(txt, p['chars'], params, cmp)

            picked_user_id = self.get_obj_property(p, task_type + '.picked_user_id')
            from_url = self.get_query_argument('from', 0) or '/task/lobby/' + task_type.split('.')[0]
            home_title = '任务大厅' if re.match(r'^/task/lobby/', from_url) else '返回'
            self.render('text_proof.html', task_type=task_type,
                        from_url=from_url, home_title=home_title,
                        origin_txt=re.split(r'[\n|]', txt.strip()),
                        readonly=readonly or picked_user_id != self.current_user['_id'],
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
    def gen_segments(txt, chars, params=None, cmp=None):

        # 先比对文本(diff)得到行号连续的文本片段元素 segments
        params = params or {}
        segments = Diff.diff(re.sub(' ', '', txt), re.sub(' ', '', cmp or txt), label=params.get('label'))[0]
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


class TextReviewHandler(TaskHandler):
    URL = '/task/do/text_review/@task_id'

    def get(self, name=''):
        """ 进入文字审定页面 """
        TextProofHandler.lock_enter(self, 'text_review', name, ('review', '文字审定'))