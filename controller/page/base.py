#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from controller import auth
from operator import itemgetter
from controller import errors as e
from controller.tool.box import Box
from controller.tool.diff import Diff
from controller.tool import variant as vt
from controller.page.page import Page
from controller.char.char import Char
from controller.task.base import TaskHandler


class PageHandler(Page, TaskHandler, Box):
    box_level = {
        'task': dict(cut_proof=1, cut_review=10),
        'role': dict(切分校对员=1, 切分审定员=10, 切分专家=100),
    }
    default_level = 1

    def __init__(self, application, request, **kwargs):
        super(PageHandler, self).__init__(application, request, **kwargs)
        self.page_title = ''

    # ----------权限相关----------
    @classmethod
    def get_required_box_level(cls, char):
        return char.get('box_level') or cls.default_level

    @classmethod
    def get_user_box_level(cls, self, task_type=None, user=None):
        """获取用户的数据等级"""
        user = user or self.current_user
        task_types = list(cls.box_level['task'].keys())
        if task_type and task_type in task_types:  # 用户以任务模式修改切分数据时，给与最低修改等级1
            return cls.prop(cls.box_level, 'task.' + task_type) or 1
        else:
            roles = auth.get_all_roles(user['roles'])
            return max([cls.prop(cls.box_level, 'role.' + role, 0) for role in roles])

    @classmethod
    def get_required_type_and_point(cls, page):
        """ 获取修改char的box所需的积分。
            积分的计算是根据任务而来的，而切分任务记录在page上而不是char上
        """
        ratio = {'cut_proof': 5000, 'cut_review': 2000}
        for task_type in ['cut_review', 'cut_proof']:
            tasks = cls.prop(page, 'tasks.' + task_type, {})
            tasks = [t for t, status in tasks.items() if status == cls.STATUS_FINISHED]
            if tasks:
                return task_type, len(tasks) * ratio.get(task_type)
        return 'cut_proof', 5000

    @staticmethod
    def get_user_point(self, task_type):
        """针对指定的任务类型，获取用户积分"""
        counts = list(self.db.task.aggregate([
            {'$match': {'task_type': task_type, 'status': self.STATUS_FINISHED, 'picked_user_id': self.user_id}},
            {'$group': {'_id': None, 'count': {'$sum': '$char_count'}}},
        ]))
        points = counts and counts[0]['count'] or 0
        return points

    @classmethod
    def check_open_edit_role(cls, user_roles):
        if '切分专家' in user_roles or '切分审定员' in user_roles:
            return True
        else:
            return e.unauthorized[0], '需要切分审定员或切分专家角色，您没有权限'

    @classmethod
    def check_box_level_and_point(cls, self, char, page, task_type=None, response_error=True):
        """检查数据等级和积分"""
        # 1.检查数据等级
        r_level = cls.get_required_box_level(char)
        u_level = cls.get_user_box_level(self, task_type)
        if int(u_level) < int(r_level):
            msg = '该字符的切分数据等级为%s，%s切分数据等级%s不够' % (r_level, '当前任务' if task_type else '您的', u_level)
            return self.send_error_msg(e.data_level_unqualified[0], msg, response_error)
        # 2.检查权限
        roles = auth.get_all_roles(self.current_user['roles'])
        if '切分专家' in roles:
            return True
        r = cls.check_open_edit_role(roles)
        if r is not True:
            return self.send_error_msg(r[0], r[1], response_error)
        # 3. 检查积分
        task_types = list(cls.box_level['task'].keys())
        if int(u_level) == int(r_level) and (not task_type or task_type not in task_types):
            if char.get('box_logs') and char['box_logs'][-1].get('user_id') == self.user_id:
                return True
            required_type, required_point = cls.get_required_type_and_point(page)
            user_point = cls.get_user_point(self, required_type)
            if int(user_point) < int(required_point):
                msg = '该字符需要%s的%s积分，您的积分%s不够' % (self.get_task_name(required_type), required_point, user_point)
                return self.send_error_msg(e.data_point_unqualified[0], msg, response_error)
        return True

    def can_write(self, box, page, task_type=None):
        return self.check_box_level_and_point(self, box, page, task_type, False) is True

    def set_box_access(self, page, task_type=None):
        """设置切分框的读写权限"""
        for b in page.get('chars') or []:
            b['readonly'] = not self.can_write(b, page, task_type)
        for b in page.get('columns') or []:
            b['readonly'] = not self.can_write(b, page, task_type)
        for b in page.get('blocks') or []:
            b['readonly'] = not self.can_write(b, page, task_type)

    # ----------用户提交----------
    def merge_txt_logs(self, user_log, char):
        """合并用户的连续修改"""
        ori_logs = char.get('txt_logs') or []
        for i in range(len(ori_logs)):
            last = len(ori_logs) - 1 - i
            if ori_logs[last].get('user_id') == self.user_id:
                ori_logs.pop(last)
            else:
                break
        user_log.update({'user_id': self.user_id, 'username': self.username, 'create_time': self.now()})
        return ori_logs + [user_log]

    @staticmethod
    def get_user_op_no(page, user_id):
        """获取用户增删改操作数量"""
        no = dict(added=0, deleted=0, changed=0)
        for field in ['blocks', 'columns', 'chars']:
            for box in page[field]:
                for log in (box.get('box_logs') or [])[::1]:
                    if log.get('user_id') == user_id:
                        no[log['op']] += 1
                        continue
        no['total'] = no['added'] + no['deleted'] + no['changed']
        return no

    def get_user_submit(self, submit_data, page, task_type=None):
        """合并用户提交和数据库中已有数据。返回中page已更新"""
        # 1.合并用户修改
        user_level = self.get_user_box_level(self, task_type)
        meta = {'user_id': self.user_id, 'username': self.username, 'create_time': self.now()}
        for box_type, ops in submit_data.get('op', {}).items():
            boxes = page.get(box_type) or []
            for op in ops or []:
                # init
                pos = {k: op.get(k) for k in ['x', 'y', 'w', 'h']}
                log = {'op': op['op'], 'pos': pos, **meta}
                i, box = None, None
                for j, b in enumerate(boxes):
                    if b.get('cid') == op['cid']:
                        i, box = j, b
                        break
                # added
                if op['op'] == 'added':
                    new_box = {**pos, 'cid': op['cid'], 'added': True, 'box_level': user_level, 'box_logs': [log]}
                    if box:
                        boxes[i] = new_box
                    else:
                        boxes.append(new_box)
                    continue
                if not box:
                    continue
                # if not self.can_write(box, page, task_type):
                #     continue
                ini_log = {'op': 'initial', 'pos': {k: box.get(k) for k in ['x', 'y', 'w', 'h']}}
                ori_logs = box.get('box_logs') or [ini_log]
                if op['op'] == 'deleted':
                    if box.get('deleted'):  # 已经删除的框不能重复删除
                        continue
                    if box.get('added'):  # 如果是自己新增的框
                        others_logs = [l for l in ori_logs if l.get('user_id') != self.user_id]
                        if not len(others_logs):  # 无其他人修改，则直接删除
                            boxes.pop(i)
                    else:  # 否则打上deleted标记
                        box.update({'deleted': True, 'box_level': user_level, 'box_logs': ori_logs + [log]})
                elif op['op'] == 'recovered':
                    if not box.get('deleted'):  # 非删除框无需恢复
                        continue
                    box_logs = [i for i in ori_logs if not (i.get('user_id') == self.user_id and i['op'] == 'deleted')]
                    if len(box_logs) == 1 and box_logs[0]['op'] == 'initial':
                        box_logs = []
                    box.update({'box_level': user_level, 'box_logs': box_logs})
                    box.pop('deleted', 0)
                elif op['op'] == 'changed':
                    length = len(ori_logs)
                    for i in range(length):  # 合并用户连续的修改记录
                        last = length - 1 - i
                        if ori_logs[last].get('user_id') == self.user_id and ori_logs[last].get('op') == 'changed':
                            ori_logs.pop(last)
                        else:
                            break
                    box.update({**pos, 'changed': True, 'box_level': user_level, 'box_logs': ori_logs + [log]})
            page[box_type] = boxes
        # 2.sub columns
        if submit_data.get('sub_columns'):
            column_dict = {c['column_id']: c for c in page['columns'] if c.get('column_id')}
            for col_id, sub_columns in submit_data.get('sub_columns').items():
                column = column_dict.get(col_id)
                if column:
                    for sub_col in sub_columns:
                        col_chars = [c for c in page['chars'] if c['cid'] in sub_col['char_cids']]
                        col_chars and sub_col.update(self.get_outer_range(col_chars))
                    column['sub_columns'] = sub_columns
        # 2.合并用户框序
        for box_type, orders in submit_data.get('order', {}).items():
            cid2box = {b['cid']: b for b in page[box_type]}
            for i, o in enumerate(orders or []):
                cid, bid = o[0], o[1]
                if cid2box.get(cid):
                    cid2box[cid]['idx'] = i
                    self.set_box_id(cid2box[cid], box_type, bid)
            page[box_type].sort(key=itemgetter('idx'))
        # 3.根据字框调整栏框、列框
        page['blocks'] = self.adjust_blocks(page['blocks'], page['chars'])
        page['columns'] = self.adjust_columns(page['columns'], page['chars'])
        # 4.保存用户序线
        page['user_links'] = submit_data.get('user_links') or {}
        return {k: page.get(k) for k in ['blocks', 'columns', 'chars', 'images', 'user_links'] if k in page}

    # ----------功能函数----------
    def get_page_img(self, page):
        page_name = self.prop(page, 'name', page)
        return self.get_web_img(page_name, 'page')

    @classmethod
    def pack_cut_boxes(cls, page, log=True, sub_columns=False):
        fields = ['x', 'y', 'w', 'h', 'cid', 'added', 'deleted', 'changed']
        log and fields.extend(['box_logs'])
        if page.get('blocks'):
            cls.pick_fields(page['blocks'], fields + ['block_no', 'block_id'])
        if page.get('columns'):
            ext = ['sub_columns'] if sub_columns else []
            cls.pick_fields(page['columns'], fields + ['block_no', 'column_no', 'column_id'] + ext)
        if page.get('chars'):
            cls.pick_fields(page['chars'], fields + ['block_no', 'column_no', 'char_no', 'char_id', 'ocr_txt', 'txt'])
        if page.get('images'):
            cls.pick_fields(page['images'], fields + ['image_id'])

    @classmethod
    def pack_txt_boxes(cls, page, log=True):
        fields = ['x', 'y', 'w', 'h', 'cid', 'added', 'deleted', 'changed']
        log and fields.extend(['box_logs', 'txt_logs'])
        if page.get('blocks'):
            cls.pick_fields(page['blocks'], fields + ['block_no', 'block_id'])
        if page.get('columns'):
            cls.pick_fields(page['columns'], fields + ['block_no', 'column_no', 'column_id', 'ocr_txt'])
        if page.get('chars'):
            ext = ['block_no', 'column_no', 'char_no', 'char_id', 'is_vague', 'is_deform', 'uncertain',
                   'alternatives', 'ocr_txt', 'ocr_col', 'cmp_txt', 'txt', 'remark']
            cls.pick_fields(page['chars'], fields + ext)
        if page.get('images'):
            cls.pick_fields(page['images'], fields + ['image_id'])

    @classmethod
    def extract_sub_col(cls, page):
        sub_cols = []
        for col in page.get('columns', []):
            if col.get('sub_columns'):
                sub_cols += col['sub_columns']
        if page.get('columns') and len(sub_cols):
            page['columns'] += sub_cols

    @classmethod
    def set_box_id(cls, box, box_type, bid):
        if not bid:
            cls.pop_fields([box], 'block_no,block_id,column_no,column_id,char_no,char_id')
        elif box_type == 'blocks':
            box['block_id'] = bid
            box['block_no'] = bid[1:]
        elif box_type == 'columns':
            box['column_id'] = bid
            box['block_no'], box['column_no'] = bid[1:].split('c')
        elif box_type == 'chars':
            box['char_id'] = bid
            box['block_no'], box['column_no'], box['char_no'] = bid[1:].split('c')
        for k in ['block_no', 'column_no', 'char_no']:
            if k in box:
                box[k] = int(box[k])

    @classmethod
    def set_char_class(cls, chars):
        for ch in chars or []:
            txts = list(set(ch[k] for k in ['ocr_txt', 'cmp_txt', 'ocr_col'] if cls.is_valid_txt(ch.get(k))))
            is_same = len(txts) == 1
            is_variant = vt.is_variants(txts)
            classes = '' if is_same else 'is_variant' if is_variant else 'diff'
            if cls.is_valid_txt(ch.get('txt')) and ch.get('txt') != ch.get('ocr_txt'):
                classes += ' changed'
            ch['class'] = classes.strip(' ')

    # ----------文本处理----------
    @staticmethod
    def is_valid_txt(txt):
        return txt not in [None, '■', '']

    @classmethod
    def get_txt(cls, page, field='txt'):
        """获取chars的文本"""

        def get_txt(box):
            t = box.get(field) or ''
            if not t and field == 'txt':
                t = page.get('cmb_txt') or page.get('ocr_txt') or ''
            return t

        chars = page.get('chars')
        if not chars:
            return ''
        pre, txt = chars[0], get_txt(chars[0]) or ''
        for c in chars[1:]:
            if c.get('deleted'):
                continue
            if pre.get('block_no') and c.get('block_no') and int(pre['block_no']) != int(c['block_no']):
                txt += '||'
            elif pre.get('column_no') and c.get('column_no') and int(pre['column_no']) != int(c['column_no']):
                txt += '|'
            txt += get_txt(c)
            pre = c
        return txt.strip('|')

    @classmethod
    def apply_ocr_col(cls, page):
        """ 将列文本和置信度适配给字框"""

        def trim_col(txt, lc):
            # 列引擎可以识别图片中的空格，适配前要去掉
            lc = lc if isinstance(lc, list) else []
            lc = [l for i, l in enumerate(lc) if txt[i] != ' ']
            return txt.replace(' ', ''), lc

        if not page.get('chars') or not page.get('columns'):
            return
        # init
        col2chars, mis_lens = {}, 0
        for c in page['chars']:
            c.pop('lc', 0)
            c.pop('ocr_col', 0)
            if c.get('deleted'):
                continue
            column_id = 'b%sc%s' % (c['block_no'], c['column_no'])
            col2chars[column_id] = col2chars.get(column_id) or []
            col2chars[column_id].append(c)
        for col in page['columns']:
            if not col.get('ocr_txt') or not col.get('block_no') or not col2chars.get(col['column_id']):
                continue
            # init ocr_col, lc_col
            ocr_col, lc_col = trim_col(col.get('ocr_txt') or '', col.get('lc') or [])
            ocr_col2, lc_col2 = '', []
            if col.get('sub_columns'):
                for sub in col['sub_columns']:
                    if isinstance(sub.get('lc'), list):
                        lc_col2 += sub.get('lc') or []
                        ocr_col2 += sub.get('ocr_txt') or ''
            ocr_col2, lc_col2 = trim_col(ocr_col2, lc_col2)
            if not ocr_col and not ocr_col2:
                continue
            # 通过diff算法，从ocr_col和ocr_col2中选择最大匹配的文本
            col_chars = col2chars[col['column_id']]
            ocr_txt = ''.join([c['ocr_txt'] for c in col_chars])
            segments = Diff.diff_line(ocr_txt, ocr_col)
            if ocr_col2 and lc_col2:
                segments2 = Diff.diff_line(ocr_txt, ocr_col2)
                len1 = sum([len(s['base']) for s in segments if s.get('is_same')])
                len2 = sum([len(s['base']) for s in segments2 if s.get('is_same')])
                if len2 > len1:
                    ocr_col, lc_col, segments = ocr_col2, lc_col2, segments2
            # 适配列文至字框
            idx1, idx2, lc_len = 0, 0, len(lc_col)
            for i, seg in enumerate(segments):
                if len(seg['base']) == len(seg['cmp']):
                    for n in range(len(seg['base'])):
                        col_chars[idx1]['ocr_col'] = ocr_col[idx2]
                        if idx2 < lc_len:
                            col_chars[idx1]['lc'] = lc_col[idx2]
                        idx1, idx2 = idx1 + 1, idx2 + 1
                else:  # 长度不一致，直接丢弃
                    idx1, idx2 = idx1 + len(seg['base']), idx2 + len(seg['cmp'])
                    mis_lens += len(seg['base'])
        # 返回失配的长度
        return mis_lens

    @classmethod
    def apply_raw_txt(cls, page, txt, field):
        """ 将txt文本适配至page['chars']。
        用txt和ocr文本diff，针对异文的几种情况：
        1. 如果ocr文本为空，则丢弃txt文本
        2. 如果ocr文本为换行，则补充txt文本为换行
        3. 如果txt文本为空，则根据ocr文本长度，填充■
        4. 如果ocr文本和txt文本长度不一致，则认为不匹配
        """
        ocr_txt, mis_len = cls.get_txt(page, 'ocr_txt'), 0
        if not ocr_txt:
            return
        segments = Diff.diff(ocr_txt, txt, filter_junk=False)[0]
        for s in segments:
            if s['is_same'] and s['base'] == '\n':
                s['cmp1'] = '\n'
            if not s.get('cmp1'):
                s['cmp1'] = '■' * len(s['base'])
            if not s.get('base'):
                s['cmp1'] = ''
            if len(s['base']) != len(s['cmp1']):
                mis_len += len(s['base'])
                s['cmp1'] = '■' * (len(s['base']))

        base_txt = ''.join([s['base'] for s in segments])
        cmp1_txt = ''.join([s['cmp1'] for s in segments])
        assert len(base_txt) == len(cmp1_txt)
        # write back
        j = 0
        cmp1_txt = re.sub(r'[\|\n]+', '', cmp1_txt)
        for i, c in enumerate(page['chars']):
            if not c.get('deleted') and c.get('ocr_txt'):
                c[field] = cmp1_txt[j]
                j += 1
        return mis_len

    @classmethod
    def html2txt(cls, html):
        """从html中获取txt文本，换行用|、换栏用||表示"""
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
        """把文本转换为html，文本以空行或者||为分栏"""
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
        """检查图文是否匹配，包括总行数和每行字数"""
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
        """将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        char_txt = ''.join([c['ocr_txt'] for c in chars if c.get('ocr_txt')])
        if len(char_txt) != len(txt):
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
    def page_diff(cls, base, cmp1='', cmp2='', cmp3=''):
        """生成文字校对的segment"""
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
            if len(s['base']) == len(s['cmp1']):
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
