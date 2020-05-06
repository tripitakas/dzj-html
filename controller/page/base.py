#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from operator import itemgetter
from .tool.box import Box
from .tool.diff import Diff
from controller import auth
from controller import errors as e
from controller import helper as hp
from tornado.escape import url_escape
from controller.page.page import Page
from controller.task.base import TaskHandler


class PageHandler(TaskHandler, Page, Box):
    box_level = {
        'task': dict(cut_proof=1, cut_review=10),
        'role': dict(切分校对员=1, 切分审定员=10, 切分专家=100),
    }
    default_level = 1

    def __init__(self, application, request, **kwargs):
        super(PageHandler, self).__init__(application, request, **kwargs)

    @classmethod
    def get_required_box_level(cls, char):
        return char.get('box_level') or cls.default_level

    @classmethod
    def get_user_box_level(cls, self, task_type=None, user=None):
        """ 获取用户的数据等级"""
        user = user or self.current_user
        if task_type:
            # 用户以任务模式修改切分数据时，给与最低修改等级1
            return hp.prop(cls.box_level, 'task.' + task_type) or 1
        else:
            roles = auth.get_all_roles(user['roles'])
            return max([hp.prop(cls.box_level, 'role.' + role, 0) for role in roles])

    @staticmethod
    def get_required_type_and_point(char):
        """ 获取修改char的txt所需的积分"""
        ratio = {'cut_proof': 1000, 'cut_review': 500}
        for task_type in ['cut_review', 'cut_proof']:
            tasks = hp.prop(char, 'tasks.' + task_type, [])
            if tasks:
                return task_type, len(tasks) * ratio.get(task_type)
        return 'cut_proof', 1000

    @staticmethod
    def get_user_point(self, task_type):
        """ 针对指定的任务类型，获取用户积分"""
        return self.db.task.count_documents({
            'task_type': task_type, 'picked_user_id': self.user_id, 'status': self.STATUS_FINISHED
        })

    @classmethod
    def check_box_level_and_point(cls, self, char, task_type=None, send_error_response=True):
        """ 检查数据等级和积分"""
        required_level = cls.get_required_box_level(char)
        user_level = cls.get_user_box_level(self, task_type)
        if int(user_level) < int(required_level):
            msg = '该字符的切分数据等级为%s，您的切分数据等级(%s)不够' % (required_level, user_level)
            if send_error_response:
                return self.send_error_response(e.data_level_unqualified, message=msg)
            else:
                return e.data_level_unqualified[0], msg
        if int(user_level) == int(required_level) and not task_type:
            required_type, required_point = cls.get_required_type_and_point(char)
            user_point = cls.get_user_point(self, required_type)
            if int(user_point) < int(required_point):
                msg = '该字符需要%s的%s积分，您的积分%s不够' % (self.get_task_name(required_type), required_point, user_point)
                if send_error_response:
                    return self.send_error_response(e.data_point_unqualified, message=msg)
                else:
                    return e.data_point_unqualified[0], msg
        return True

    def can_write(self, box, task_type=None):
        return self.check_box_level_and_point(self, box, task_type, False) is True

    def set_box_access(self, page, task_type=None):
        """ 设置切分框的读写权限"""
        for b in page['blocks']:
            b['readonly'] = not self.can_write(b, task_type)
        for b in page['chars']:
            b['readonly'] = not self.can_write(b, task_type)
        for b in page['columns']:
            b['readonly'] = not self.can_write(b, task_type)

    def pack_boxes(self, page):
        self.pop_fields(page['chars'], 'box_logs')
        self.pop_fields(page['blocks'], 'box_logs')
        self.pop_fields(page['columns'], 'box_logs')

    @staticmethod
    def apply_col_txt(page):
        """ 将columns的ocr_txt赋值给chars字段col_txt"""
        changed = False
        for co in page.get('columns', []):
            chars = [c for c in page['chars'] if c['block_no'] == co['block_no'] and c['column_no'] == co['column_no']]
            chars.sort(key=itemgetter('block_no', 'column_no', 'char_no'))
            co_txt = co['ocr_txt']
            length = len(chars)
            if len(co_txt) == length:  # 字数相等
                changed = True
                for i, c in enumerate(chars):
                    c['col_txt'] = co_txt[i]
            elif len(co_txt) == length - 1:  # 字数少1
                changed = True
                for i, c in enumerate(chars):
                    cot = co_txt[i] if i < length - 1 else ''
                    cont = co_txt[i + 1] if i < length - 2 else ''
                    cnt = chars[i + 1].get('ocr_txt') if i < length - 1 else ''
                    cnnt = chars[i + 2].get('ocr_txt') if i < length - 2 else ''
                    if not c.get('ocr_txt') and cot != cnt:
                        c['col_txt'] = c['ocr_txt'] = cot
                    elif cot != c.get('ocr_txt') and (cot == cnt or cont == cnnt):
                        c['col_txt'] = ''
                        co_txt = co_txt[:i] + '□' + co_txt[i:]
                    else:
                        c['col_txt'] = cot
            else:
                co['un_equal'] = True
        return changed

    @staticmethod
    def apply_cmp_txt(page):
        """ 将寻找的比对文本逐个赋值给chars字段cmp_txt"""
        changed = False
        return changed

    def merge_post_boxes(self, post_boxes, box_type, page, task_type=None):
        """ 合并用户提交和数据库中已有数据"""
        post_box_dict = {b['cid']: b for b in post_boxes if b.get('cid')}
        # 检查删除
        post_cids = [b['cid'] for b in post_boxes if b.get('cid')]
        to_delete = [b for b in page[box_type] if b['cid'] not in post_cids]
        can_delete = [b['cid'] for b in to_delete if self.can_write(b, task_type)]
        cannot_delete = [b['cid'] for b in to_delete if b['cid'] not in can_delete]
        boxes = [b for b in page[box_type] if b['cid'] not in can_delete]
        # 检查修改
        change_cids = [b.get('cid') for b in post_boxes if b.get('changed') is True]
        to_change = [b for b in boxes if b['cid'] in change_cids]
        can_change = [b for b in to_change if self.can_write(b, task_type)]
        cannot_change = [b['cid'] for b in to_change if b['cid'] not in can_delete]
        for b in can_change:
            b.pop('changed', 0)
            pb = post_box_dict.get(b['cid'])
            if self.is_box_pos_equal(b, pb):
                continue
            update = {k: pb.get(k) for k in ['x', 'y', 'w', 'h']}
            my_log = {**update, 'user_id': self.user_id, 'username': self.username, 'create_time': self.now()}
            box_logs = b.get('box_logs') or [{k: b.get(k) for k in ['x', 'y', 'w', 'h']}]
            box_logs.append(my_log)
            status = 'added#changed' if b.get('status') == 'added' else 'changed'
            update.update({'box_logs': box_logs, 'status': status})
            b.update(update)
        # 检查新增
        added = [b for b in post_boxes if b.get('added') is True]
        for pb in added:
            pb.pop('added', 0)
            update = {k: pb.get(k) for k in ['x', 'y', 'w', 'h']}
            my_log = {**update, 'user_id': self.user_id, 'username': self.username, 'create_time': self.now()}
            pb.update({'box_logs': [my_log], 'status': 'added'})
        boxes.extend(added)
        page[box_type] = boxes
        return boxes, cannot_delete, cannot_change

    def get_box_update(self, post_data, page):
        """ 获取切分校对的提交"""
        # 合并用户提交和已有数据
        self.merge_post_boxes(post_data['chars'], 'chars', page)
        self.merge_post_boxes(post_data['blocks'], 'blocks', page)
        self.merge_post_boxes(post_data['columns'], 'columns', page)
        # 过滤页面外的切分框
        blocks, columns, chars = self.filter_box(page, page['width'], page['height'])
        # 更新cid
        self.update_box_cid(chars)
        self.update_box_cid(blocks)
        self.update_box_cid(columns)
        # 重新排序
        blocks = self.calc_block_id(blocks)
        columns = self.calc_column_id(columns, blocks)
        chars = self.calc_char_id(chars, columns)
        # 根据字框调整列框和栏框的边界
        if post_data.get('auto_adjust'):
            blocks = self.adjust_blocks(blocks, chars)
            columns = self.adjust_columns(columns, chars)

        return dict(chars=chars, blocks=blocks, columns=columns)

    def get_txt(self, page, key):
        if key == 'txt':
            return page.get('txt') or ''
        if key == 'cmp':
            return page.get('cmp') or ''
        if key == 'ocr':
            return self.get_box_ocr(page.get('chars'))
        if key == 'ocr_col':
            return self.get_box_ocr(page.get('columns'))

    def get_txts(self, page):
        txts = [(self.get_txt(page, f), f, Page.get_field_name(f)) for f in ['txt', 'ocr', 'ocr_col', 'cmp']]
        txts = [t for t in txts if t[0]]
        return txts

    @classmethod
    def get_box_ocr(cls, boxes):
        """ 获取chars或columns里的ocr文本"""
        if not boxes:
            return ''
        pre = boxes[0]
        txt = pre.get('ocr_txt', '')
        for b in boxes[1:]:
            if pre.get('block_no') and b.get('block_no') and pre['block_no'] != b['block_no']:
                txt += '||'
            elif pre.get('column_no') and b.get('column_no') and pre['column_no'] != b['column_no']:
                txt += '|'
            txt += b.get('ocr_txt', '')
            pre = b
        return txt.strip('|')

    @classmethod
    def txt2html(cls, txt):
        """ 把文本转换为html，文本以空行或者||为分栏"""
        if re.match('<[a-z]+.*>.*</[a-z]+>', txt):
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
    def char2html(cls, chars, field='txt'):
        if not chars:
            return ''
        pre, html = chars[0], '<div class="blocks"><div class="block"><div class="line">'
        html += '<span id="%s" class="char">%s</span>' % (pre['cid'], pre[field])
        for b in chars[1:]:
            if pre.get('block_no') and b.get('block_no') and pre['block_no'] != b['block_no']:
                html += '</div></div><div class="block"><div class="line">'
            elif pre.get('column_no') and b.get('column_no') and pre['column_no'] != b['column_no']:
                html += '</div><div class="line">'
            if b.get(field):
                html += '<span id="%s" class="char">%s</span>' % (b['cid'], b[field])
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

    def get_cmp_data(self):
        """ 获取比对文本、存疑文本"""
        texts, doubts = [], []
        if 'text_proof_' in self.task_type:
            doubts.append([self.prop(self.task, 'result.doubt', ''), '我的存疑'])
            for field in ['text', 'ocr', 'ocr_col', 'cmp']:
                if self.get_txt(field):
                    texts.append([self.get_txt(field), field, Page.get_field_name(field)])
        elif self.task_type == 'text_review':
            doubts.append([self.prop(self.task, 'result.doubt', ''), '我的存疑'])
            proof_doubt = ''
            condition = dict(task_type={'$regex': 'text_proof'}, doc_id=self.page_name, status=self.STATUS_FINISHED)
            for task in list(self.db.task.find(condition)):
                txt = self.html2txt(self.prop(task, 'result.txt_html', ''))
                texts.append([txt, task['task_type'], self.get_task_name(task['task_type'])])
                proof_doubt += self.prop(task, 'result.doubt', '')
            if proof_doubt:
                doubts.append([proof_doubt, '校对存疑'])
        elif self.task_type == 'text_hard':
            doubts.append([self.prop(self.task, 'result.doubt', ''), '难字列表'])
            condition = dict(task_type='text_review', doc_id=self.page['name'], status=self.STATUS_FINISHED)
            review_task = self.db.task.find_one(condition)
            review_doubt = self.prop(review_task, 'result.doubt', '')
            if review_doubt:
                doubts.append([review_doubt, '审定存疑'])
        return texts, doubts

    def get_txt_html_update(self, txt_html):
        """ 获取page的txt_html字段的更新"""
        text = self.html2txt(txt_html)
        is_match = self.check_match(self.page.get('chars'), text)[0]
        update = {'text': text, 'txt_html': txt_html, 'is_match': is_match}
        if is_match:
            update['chars'] = self.update_chars_txt(self.page.get('chars'), text)
        return update

    @classmethod
    def check_utf8mb4(cls, seg, base=None):
        column_strip = re.sub(r'\s', '', base or seg.get('base', ''))
        char_codes = [(c, url_escape(c)) for c in list(column_strip)]
        seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])
        return seg

    @staticmethod
    def check_match(chars, txt):
        """ 检查图文是否匹配，包括总行数和每行字数"""
        # 获取每列字框数
        column_char_num = []
        if chars:
            pre, num = chars[0], 1
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:  # 换栏
                    column_char_num.append(num)
                    num = 1
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:  # 换行
                    column_char_num.append(num)
                    num = 1
                else:
                    num += 1
            column_char_num.append(num)
        # 获取每行文字数
        txt_lines = re.sub(r'[\|\n]+', '|', txt).split('|')
        line_char_num = [len(line) for line in txt_lines]
        # 进行比对检查
        mis_match = []
        if len(column_char_num) < len(line_char_num):
            for i, num in enumerate(column_char_num):
                if num != line_char_num[i]:
                    mis_match.append([i, num, line_char_num[i]])
            for i in range(len(column_char_num), len(line_char_num)):
                mis_match.append([i, 0, line_char_num[i]])
        else:
            for i, num in enumerate(line_char_num):
                if num != column_char_num[i]:
                    mis_match.append([i, column_char_num[i], num])
            for i in range(len(line_char_num), len(column_char_num)):
                mis_match.append([i, column_char_num[i], 0])
        # 输出结果，r表示是否匹配，mis_match表示不匹配的情况
        r = len(column_char_num) == len(line_char_num) and not mis_match
        return r, mis_match, column_char_num, line_char_num

    @staticmethod
    def update_chars_txt(chars, txt):
        """ 将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        if len(chars) != len(txt):
            return False
        for i, c in enumerate(chars):
            c['txt'] = txt[i]
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
