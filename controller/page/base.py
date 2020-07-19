#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from operator import itemgetter
from .tool.box import Box
from .tool.diff import Diff
from controller import auth
from controller import errors as e
from controller import helper as hp
from controller.page.page import Page
from controller.task.base import TaskHandler
from controller.page.tool import variant as v


class PageHandler(TaskHandler, Page, Box):
    box_level = {
        'task': dict(cut_proof=1, cut_review=10),
        'role': dict(切分校对员=1, 切分审定员=10, 切分专家=100),
    }
    default_level = 1

    def __init__(self, application, request, **kwargs):
        super(PageHandler, self).__init__(application, request, **kwargs)
        self.page_title = ''

    @classmethod
    def get_required_box_level(cls, char):
        return char.get('box_level') or cls.default_level

    @classmethod
    def get_user_box_level(cls, self, task_type=None, user=None):
        """ 获取用户的数据等级"""
        user = user or self.current_user
        task_types = list(cls.box_level['task'].keys())
        if task_type and task_type in task_types:
            # 用户以任务模式修改切分数据时，给与最低修改等级1
            return hp.prop(cls.box_level, 'task.' + task_type) or 1
        else:
            roles = auth.get_all_roles(user['roles'])
            return max([hp.prop(cls.box_level, 'role.' + role, 0) for role in roles])

    @classmethod
    def get_required_type_and_point(cls, page):
        """ 获取修改char的box所需的积分。
            积分的计算是根据任务而来的，而切分任务记录在page上而不是char上
        """
        ratio = {'cut_proof': 5000, 'cut_review': 2000}
        for task_type in ['cut_review', 'cut_proof']:
            tasks = hp.prop(page, 'tasks.' + task_type, {})
            tasks = [t for t, status in tasks.items() if status == cls.STATUS_FINISHED]
            if tasks:
                return task_type, len(tasks) * ratio.get(task_type)
        return 'cut_proof', 5000

    @staticmethod
    def get_user_point(self, task_type):
        """ 针对指定的任务类型，获取用户积分"""
        condition = {'task_type': task_type, 'picked_user_id': self.user_id, 'status': self.STATUS_FINISHED}
        tasks = list(self.db.task.find(condition, {'char_count': 1}))
        return sum([t['char_count'] for t in tasks])

    @classmethod
    def check_box_level_and_point(cls, self, char, page, task_type=None, send_error_response=True):
        """ 检查数据等级和积分"""
        required_level = cls.get_required_box_level(char)
        user_level = cls.get_user_box_level(self, task_type)
        if int(user_level) < int(required_level):
            msg = '该字符的切分数据等级为%s，您的切分数据等级%s不够' % (required_level, user_level)
            if send_error_response:
                return self.send_error_response(e.data_level_unqualified, message=msg)
            else:
                return e.data_level_unqualified[0], msg
        roles = auth.get_all_roles(self.current_user['roles'])
        if '切分专家' in roles:
            return True
        task_types = list(cls.box_level['task'].keys())
        if int(user_level) == int(required_level) and (not task_type or task_type not in task_types):
            if char.get('box_logs') and char['box_logs'][-1].get('user_id') == self.user_id:
                return True
            required_type, required_point = cls.get_required_type_and_point(page)
            user_point = cls.get_user_point(self, required_type)
            if int(user_point) < int(required_point):
                msg = '该字符需要%s的%s积分，您的积分%s不够' % (self.get_task_name(required_type), required_point, user_point)
                if send_error_response:
                    return self.send_error_response(e.data_point_unqualified, message=msg)
                else:
                    return e.data_point_unqualified[0], msg
        return True

    def can_write(self, box, page, task_type=None):
        return self.check_box_level_and_point(self, box, page, task_type, False) is True

    def set_box_access(self, page, task_type=None):
        """ 设置切分框的读写权限"""
        for b in page['chars']:
            b['readonly'] = not self.can_write(b, page, task_type)
        for b in page['columns']:
            b['readonly'] = not self.can_write(b, page, task_type)
        for b in page['blocks']:
            b['readonly'] = not self.can_write(b, page, task_type)

    @classmethod
    def pack_boxes(cls, page, extract_sub_columns=False, pop_char_logs=True):
        if extract_sub_columns:
            for col in page['columns']:
                if col.get('sub_columns'):
                    page['columns'].extend(col['sub_columns'])
        fields1 = ['x', 'y', 'w', 'h', 'cid', 'block_no', 'block_id']
        fields2 = ['x', 'y', 'w', 'h', 'cid', 'block_no', 'column_no', 'column_id', 'ocr_txt']
        fields3 = ['x', 'y', 'w', 'h', 'cid', 'block_no', 'column_no', 'char_no', 'char_id', 'cc',
                   'alternatives', 'ocr_txt', 'ocr_col', 'cmp_txt', 'txt']
        cls.pick_fields(page['blocks'], fields1)
        cls.pick_fields(page['columns'], fields2)
        if not pop_char_logs:
            fields3 = fields3 + ['box_logs', 'txt_logs']
        cls.pick_fields(page['chars'], fields3)

    @classmethod
    def filter_symbol(cls, txt):
        """ 过滤校勘符号"""
        return re.sub(r'[YMN]', '', txt)

    @classmethod
    def apply_txt(cls, page, field):
        """ 适配文本至page['chars']，包括ocr_col, cmp_txt, txt等几种情况
        用field文本和ocr文本进行diff，针对异文的几种情况：
        1. 如果ocr文本为空，则丢弃field文本
        2. 如果ocr文本为换行，则补充field文本为换行
        3. 如果field文本为空，则根据ocr文本长度，填充■
        4. 如果ocr文本和field文本长度不一致，则认为不匹配
        """
        if cls.prop(page, 'txt_match.' + field) in [True, False]:
            return page['txt_match'][field]
        match = True
        diff_segments = Diff.diff(cls.get_txt(page, 'ocr'), cls.get_txt(page, field))[0]
        for s in diff_segments:
            if s['is_same'] and s['base'] == '\n':
                s['cmp1'] = '\n'
            if not s.get('cmp1'):
                s['cmp1'] = '■' * len(s['base'])
            if not s.get('base'):
                s['cmp1'] = ''
            if len(s['base']) != len(cls.filter_symbol(s['cmp1'])):
                match = False
                _cmp1 = cls.filter_symbol(s['cmp1'])
                if len(_cmp1) < len(s['base']):
                    s['cmp1'] += '■' * (len(s['base']) - len(_cmp1))
                else:
                    s['cmp1'] = '■' * (len(s['base']))

        ocr_txt = ''.join([s['base'] for s in diff_segments])
        txt2apply = ''.join([s['cmp1'] for s in diff_segments])
        assert len(ocr_txt) == len(cls.filter_symbol(txt2apply))
        cls.write_back_txt(page['chars'], txt2apply, field)
        return match, txt2apply

    def merge_txt_logs(self, user_log, txt_logs):
        """ 合并log至txt_logs中。如果用户已在txt_logs中，则更新用户已有的log；否则，新增一条log"""
        is_new = True
        txt_logs = txt_logs or []
        user_log['updated_time'] = self.now()
        for i, log in enumerate(txt_logs):
            if log.get('user_id') == self.user_id:
                log.update(user_log)
                is_new = False
        if is_new:
            user_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
            txt_logs.append(user_log)
        return txt_logs

    def merge_box_logs(self, user_log, box_logs):
        """ 合并log至box_logs中。如果用户已在box_logs中，则更新用户已有的log；否则，新增一条log"""
        assert 'pos' in user_log
        is_new = True
        box_logs = box_logs or []
        user_log['updated_time'] = self.now()
        for i, log in enumerate(box_logs):
            if log.get('user_id') == self.user_id:
                log.update(user_log)
                is_new = False
        if is_new:
            user_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
            box_logs.append(user_log)
        return box_logs

    def merge_post_boxes(self, post_boxes, box_type, page, task_type=None):
        """ 合并用户提交和数据库中已有数据，过程中将进行权限检查"""
        user_level = self.get_user_box_level(self, task_type)
        post_cids = [b['cid'] for b in post_boxes if b.get('cid')]
        page_cids = [b['cid'] for b in page[box_type] if b.get('cid')]
        post_box_dict = {b['cid']: b for b in post_boxes if b.get('cid')}
        # 检查删除
        to_delete = [b for b in page[box_type] if not b.get('cid') or b['cid'] not in post_cids]
        deleted = [b['cid'] for b in to_delete if self.can_write(b, page, task_type)]
        # cannot_delete = [b['cid'] for b in to_delete if b['cid'] not in can_delete]
        boxes = [b for b in page[box_type] if not b.get('cid') or b['cid'] not in deleted]  # 删除可删除的字框，保留其它字框
        # 检查修改
        change_cids = [b['cid'] for b in post_boxes if b.get('changed') is True]
        to_change = [b for b in boxes if b['cid'] in change_cids]
        can_change = [b for b in to_change if self.can_write(b, page, task_type)]
        # cannot_change = [b['cid'] for b in to_change if b['cid'] not in can_change]
        changed = []
        for b in can_change:
            pb = post_box_dict.get(b['cid'])
            if self.is_box_pos_equal(b, pb):
                b.pop('changed', 0)
                continue
            pos = {k: pb.get(k) for k in ['x', 'y', 'w', 'h']}
            old_logs = b.get('box_logs') or [{k: b.get(k) for k in ['x', 'y', 'w', 'h']}]
            box_logs = self.merge_box_logs({'pos': pos}, old_logs)
            b.update({**pos, 'box_level': user_level, 'box_logs': box_logs})
            changed.append({'cid': b['cid'], 'pos': {'x': b['x'], 'y': b['y'], 'w': b['w'], 'h': b['h']}})
        # 检查新增
        to_add = [b for b in post_boxes if b.get('added') is True]
        can_add = []
        added = []
        for pb in to_add:
            pb.pop('added', 0)
            if pb['cid'] in page_cids or pb.get('changed'):
                continue
            update = {k: pb.get(k) for k in ['x', 'y', 'w', 'h']}
            my_log = {**update, 'user_id': self.user_id, 'username': self.username, 'create_time': self.now()}
            pb.update({'ocr_txt': '■', 'box_level': user_level, 'box_logs': [my_log], 'new': True})
            can_add.append(pb)
            added.append({'cid': pb['cid'], 'pos': {'x': pb['x'], 'y': pb['y'], 'w': pb['w'], 'h': pb['h']}})
        boxes.extend(can_add)
        page[box_type] = boxes
        return dict(deleted=deleted, changed=changed, added=added)

    def get_box_update(self, post_data, page, task_type=None):
        """ 获取切分校对的提交"""
        # 预处理
        self.pop_fields(post_data['chars'], 'readonly,class')
        self.pop_fields(post_data['blocks'], 'readonly,class,char_id,char_no')
        self.pop_fields(post_data['columns'], 'readonly,class,char_id,char_no')
        self.update_page_cid(post_data)
        # 合并用户提交和已有数据
        self.merge_post_boxes(post_data['blocks'], 'blocks', page, task_type)
        self.merge_post_boxes(post_data['columns'], 'columns', page, task_type)
        char_updated = self.merge_post_boxes(post_data['chars'], 'chars', page, task_type)
        # 过滤页面外的切分框
        blocks, columns, chars = self.filter_box(page, page['width'], page['height'])
        # 切分框重新排序
        blocks = self.calc_block_id(blocks)
        columns = self.calc_column_id(columns, blocks)
        chars = self.calc_char_id(chars, columns)
        if page.get('chars_col'):  # 合并用户字序
            algorithm_chars_col = self.get_chars_col(chars)
            page['chars_col'] = self.merge_chars_col(algorithm_chars_col, page['chars_col'])
            chars = self.update_char_order(chars, page['chars_col'])
        # 根据字框调整列框和栏框的边界
        if post_data.get('auto_adjust'):
            blocks = self.adjust_blocks(blocks, chars)
            columns = self.adjust_columns(columns, chars)
        page_updated = dict(chars=chars, blocks=blocks, columns=columns, chars_col=page['chars_col'])
        return page_updated, char_updated

    @classmethod
    def get_txt(cls, page, key):
        if key == 'txt':
            return page.get('txt') or ''
        if key == 'cmp_txt':
            return page.get('cmp_txt') or ''
        if key == 'ocr':
            return cls.get_char_txt(page) or page.get('ocr')
        if key == 'ocr_col':
            return cls.get_column_txt(page) or page.get('ocr_col')

    @classmethod
    def get_txts(cls, page, fields=None):
        fields = fields or ['txt', 'ocr', 'ocr_col', 'cmp_txt']
        txts = [(cls.get_txt(page, f), f, Page.get_field_name(f)) for f in fields]
        return [t for t in txts if t[0]]

    @classmethod
    def get_column_txt(cls, page, field='ocr_txt'):
        """ 获取columns的文本"""

        def get_txt(box):
            if box.get('sub_columns') and len(box['sub_columns']) > 1 and box['sub_columns'][1].get(field):
                return ''.join([c.get(field) or '' for c in box['sub_columns']])
            return box.get(field) or ''

        boxes = page.get('columns')
        if not boxes:
            return ''
        pre, txt = boxes[0], get_txt(boxes[0])
        for b in boxes[1:]:
            if pre.get('block_no') and b.get('block_no') and int(pre['block_no']) != int(b['block_no']):
                txt += '||'
            elif pre.get('column_no') and b.get('column_no') and int(pre['column_no']) != int(b['column_no']):
                txt += '|'
            txt += get_txt(b)
            pre = b
        return txt.strip('|')

    @classmethod
    def get_char_txt(cls, page, field='ocr_txt'):
        """ 获取chars的文本"""

        def get_txt(box):
            if field == 'adapt':
                return box.get('txt') or box.get('ocr_txt') or box.get('ocr_col') or ''
            if field == 'ocr_txt':
                return box['alternatives'][0] if box.get('alternatives') else box.get('ocr_txt', '')
            return box.get(field) or ''

        boxes = page.get('chars')
        if not boxes:
            return ''
        pre, txt = boxes[0], get_txt(boxes[0])
        for b in boxes[1:]:
            if pre.get('block_no') and b.get('block_no') and int(pre['block_no']) != int(b['block_no']):
                txt += '||'
            elif pre.get('column_no') and b.get('column_no') and int(pre['column_no']) != int(b['column_no']):
                txt += '|'
            txt += get_txt(b)
            pre = b
        return txt.strip('|')

    @classmethod
    def set_char_class(cls, chars):
        for ch in chars or []:
            txts = list(set(ch[k] for k in ['ocr_txt', 'cmp_txt', 'ocr_col'] if ch.get(k) not in [None, '■']))
            is_same = len(txts) == 1
            is_variant = v.is_variants(txts)
            classes = '' if is_same else 'is_variant' if is_variant else 'diff'
            if ch.get('txt') and ch.get('txt') != ch.get('ocr_txt'):
                classes += ' changed'
            ch['class'] = classes

    @classmethod
    def char2html(cls, chars):
        def span(ch):
            classes = 'char ' + ch['class'] if ch['class'] else 'char'
            txt = ch.get('txt') if ch.get('txt') not in [None, '■'] else ch.get('ocr_txt') or '■'
            return '<span id="%s" class="%s">%s</span>' % (ch['cid'], classes, txt)

        if not chars:
            return ''
        cls.set_char_class(chars)
        pre, html = chars[0], '<div class="blocks"><div class="block"><div class="line">'
        html += span(chars[0])
        for b in chars[1:]:
            if pre.get('block_no') and b.get('block_no') and int(pre['block_no']) != int(b['block_no']):
                html += '</div></div><div class="block"><div class="line">'
            elif pre.get('column_no') and b.get('column_no') and int(pre['column_no']) != int(b['column_no']):
                html += '</div><div class="line">'
            html += span(b)
            pre = b
        return html + '</div></div></div>'

    @classmethod
    def html2txt(cls, html):
        """ 从html中获取txt文本，换行用|、换栏用||表示"""
        txt = ''
        html = re.sub('&nbsp;', '', html)
        regex1 = re.compile("<ul.*?>.*?</ul>", re.M | re.S)
        regex2 = re.compile("<li.*?>.*?</li>", re.M | re.S)
        regex3 = re.compile("<span.*?</span>", re.M | re.S)
        regex4 = re.compile("<span.*>(.*)</span>", re.M | re.S)
        for block in regex1.findall(html or ''):
            for line in regex2.findall(block or ''):
                if 'delete' not in line:
                    line_txt = ''
                    for span in regex3.findall(line or ''):
                        line_txt += ''.join(regex4.findall(span or ''))
                    txt += line_txt + '|'
            txt += '|'
        return re.sub(r'\|{2,}', '||', txt.rstrip('|'))

    @classmethod
    def txt2html(cls, txt):
        """ 把文本转换为html，文本以空行或者||为分栏"""
        if not txt:
            return ''
        if isinstance(txt, str) and re.match('<[a-z]+.*>.*</[a-z]+>', txt):
            return txt
        txt = '|'.join(txt) if isinstance(txt, list) else txt
        assert isinstance(txt, str)
        html, blocks = '', txt.split('||')
        line = '<li class="line"><span contenteditable="true" class="same" base="%s">%s</span></li>'
        for block in blocks:
            lines = block.split('|')
            html += '<ul class="block">%s</ul>' % ''.join([line % (l, l) for l in lines])
        return html

    @classmethod
    def check_match(cls, chars, txt):
        """ 检查图文是否匹配，包括总行数和每行字数"""
        txt = cls.filter_symbol(txt)
        # 获取每列字框数
        column_char_num = []
        if chars:
            pre, num = chars[0], 1
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and int(pre['block_no']) != int(c['block_no']):  # 换栏
                    column_char_num.append(num)
                    num = 1
                elif pre.get('column_no') and c.get('column_no') and int(pre['column_no']) != int(c['column_no']):  # 换行
                    column_char_num.append(num)
                    num = 1
                else:
                    num += 1
                pre = c
            column_char_num.append(num)
        # 获取每行文字数
        txt_lines = txt if isinstance(txt, list) else re.sub(r'[\|\n]+', '|', txt).split('|')
        line_char_num = [len(line) for line in txt_lines]
        # 进行比对检查
        mis_match = []
        if len(column_char_num) < len(line_char_num):
            for i, num in enumerate(column_char_num):
                if num != line_char_num[i]:
                    mis_match.append([i + 1, num, line_char_num[i]])
            for i in range(len(column_char_num), len(line_char_num)):
                mis_match.append([i + 1, 0, line_char_num[i]])
        else:
            for i, num in enumerate(line_char_num):
                if num != column_char_num[i]:
                    mis_match.append([i + 1, column_char_num[i], num])
            for i in range(len(line_char_num), len(column_char_num)):
                mis_match.append([i + 1, column_char_num[i], 0])
        # 输出结果，r表示是否匹配，mis_match表示不匹配的情况
        r = len(column_char_num) == len(line_char_num) and not mis_match
        return dict(status=r, mis_match=mis_match, column_char_num=column_char_num, line_char_num=line_char_num)

    @classmethod
    def write_back_txt(cls, chars, txt, field):
        """ 将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        char_txt = ''.join([c['ocr_txt'] for c in chars if c.get('ocr_txt')])
        if len(char_txt) != len(cls.filter_symbol(txt)):
            return False
        j = 0
        for i, c in enumerate(chars):
            if not c.get('ocr_txt'):
                continue
            if txt[j] in ['Y', 'M', 'N']:
                chars[i - 1]['txt_type'] = txt[j]
                j += 1
            c[field] = txt[j]
            j += 1

        return chars

    @classmethod
    def diff(cls, base, cmp1='', cmp2='', cmp3=''):
        """ 生成文字校对的segment"""
        # 1.生成segments
        segments = []
        pre_empty_line_no = 0
        block_no, line_no = 1, 1
        diff_segments = Diff.diff(base, cmp1, cmp2, cmp3)[0]
        for s in diff_segments:
            if s['is_same'] and s['base'] == '\n':  # 当前为空行，即换行
                if not pre_empty_line_no:  # 连续空行仅保留第一个
                    s['block_no'], s['line_no'] = block_no, line_no
                    segments.append(s)
                    line_no += 1
                pre_empty_line_no += 1
            else:  # 当前非空行
                if pre_empty_line_no > 1:  # 之前有多个空行，即换栏
                    line_no = 1
                    block_no += 1
                s['block_no'], s['line_no'] = block_no, line_no
                segments.append(s)
                pre_empty_line_no = 0
        # 2.结构化，以便页面输出
        blocks = {}
        for s in segments:
            b_no, l_no = s['block_no'], s['line_no']
            if not blocks.get(b_no):
                blocks[b_no] = {}
            if not blocks[b_no].get(l_no):
                blocks[b_no][l_no] = []
            if s['is_same'] and s['base'] == '\n':  # 跳过空行
                continue
            if s['base'] in [' ', '\u3000'] and not s.get('cmp1') and not s.get('cmp2'):
                s['is_same'] = True
            s['offset'] = s['range'][0]
            blocks[b_no][l_no].append(s)
        return blocks

    @classmethod
    def match_diff(cls, ocr_char, cmp1):
        """ 生成文字匹配的segment
        :param ocr_char OCR切分文本
        :param cmp1 列文本、比对文本(从cbeta选择得到)或校对结果
        针对异文的几种情况，处理如下：
        1. ocr_char为空，直接舍弃该segment
        2. ocr_char不为空而cmp1为空，则根据ocr_char的长度自动补齐cmp(占位符为□)
        3. 如果ocr_char和cmp1的长度相同，则视为同文
        注：算法会在segments中将base和cmp1进行对调，以便前端显示
        """
        segments = []
        pre_empty_line_no = 0
        block_no, line_no = 1, 1
        diff_segments = Diff.diff(ocr_char, cmp1)[0]
        # 1. 处理异文的几种情况
        diff_segments = [s for s in diff_segments if s['base']]
        for s in diff_segments:
            if s['is_same'] and s['base'] == '\n':
                s['cmp1'] = '\n'
            if not s['is_same'] and not s['cmp1']:
                s['cmp1'] = '■' * len(s['base'])
            if len(s['base']) == len(cls.filter_symbol(s['cmp1'])):
                s['is_same'] = True
            s['base'], s['cmp1'] = s['cmp1'], s['base']
        # 2. 设置栏号和行号
        for s in diff_segments:
            if s['is_same'] and s['base'] == '\n':  # 当前为空行，即换行
                if not pre_empty_line_no:  # 连续空行仅保留第一个
                    s['block_no'], s['line_no'] = block_no, line_no
                    segments.append(s)
                    line_no += 1
                pre_empty_line_no += 1
            else:  # 当前非空行
                if pre_empty_line_no > 1:  # 之前有多个空行，即换栏
                    line_no = 1
                    block_no += 1
                s['block_no'], s['line_no'] = block_no, line_no
                segments.append(s)
                pre_empty_line_no = 0
        # 3.结构化，以便页面输出
        blocks = {}
        for s in segments:
            b_no, l_no = s['block_no'], s['line_no']
            if not blocks.get(b_no):
                blocks[b_no] = {}
            if not blocks[b_no].get(l_no):
                blocks[b_no][l_no] = []
            if s['is_same'] and s['base'] == '\n':  # 跳过空行
                continue
            s['offset'] = s['range'][0]
            blocks[b_no][l_no].append(s)
        return blocks
