#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 页
@time: 2019/6/3
"""
import re
from operator import itemgetter
from functools import cmp_to_key
from controller.page.diff import Diff
from tornado.escape import url_escape


class PageTool(object):

    @staticmethod
    def pop_fields(boxes, fields):
        """ 清空boxes中的fields字段"""
        assert type(fields) in [str, list]
        fields = fields.replace(' ', '').split(',') if isinstance(fields, str) else fields
        for b in boxes:
            for field in fields:
                b.pop(field, 0)

    @staticmethod
    def point_in_box(point, box):
        """ 判断point是否在box内"""
        return (box['x'] <= point[0] <= box['x'] + box['w']) and (box['y'] <= point[1] <= box['y'] + box['h'])

    @staticmethod
    def line_overlap(line1, line2, only_check=False):
        """ 计算两条线段的交叉长度和比例"""
        p11, p12, w1 = line1[0], line1[1], line1[1] - line1[0]
        p21, p22, w2 = line2[0], line2[1], line2[1] - line2[0]
        if p11 > p22 or p21 > p12:
            return False if only_check else (0, 0, 0)
        if only_check:
            return True
        else:
            overlap = w1 + w2 - (max(p12, p22) - min(p11, p21))
            ratio1 = round(overlap / w1, 2)
            ratio2 = round(overlap / w2, 2)
            return overlap, ratio1, ratio2

    @staticmethod
    def box_overlap(box1, box2, only_check=False):
        """ 计算两个框的交叉面积和比例。如果only_check为True，则只要有一点交叉就返回True"""
        x1, y1, w1, h1 = box1['x'], box1['y'], box1['w'], box1['h']
        x2, y2, w2, h2 = box2['x'], box2['y'], box2['w'], box2['h']
        if x1 > x2 + w2 or x2 > x1 + w1:
            return False if only_check else (0, 0, 0)
        if y1 > y2 + h2 or y2 > y1 + h1:
            return False if only_check else (0, 0, 0)
        if only_check:
            return True
        else:
            col = abs(min(x1 + w1, x2 + w2) - max(x1, x2))
            row = abs(min(y1 + h1, y2 + h2) - max(y1, y2))
            overlap = col * row
            ratio1 = round(overlap / (w1 * h1), 2)
            ratio2 = round(overlap / (w2 * h2), 2)
            return overlap, ratio1, ratio2

    @classmethod
    def is_box_intersected(cls, a, b, direction='', ratio=0.0):
        """ a和b两个box在x轴、y轴或面积上的交叉比例是否超过ratio"""
        if not direction:
            overlap, ratio1, ratio2 = cls.box_overlap(a, b)
            return ratio1 >= ratio or ratio2 >= ratio
        elif direction == 'x':
            overlap, ratio1, ratio2 = cls.line_overlap((a['x'], a['x'] + a['w']), (b['x'], b['x'] + b['w']))
            return ratio1 >= ratio or ratio2 >= ratio
        elif direction == 'y':
            overlap, ratio1, ratio2 = cls.line_overlap((a['y'], a['y'] + a['h']), (b['y'], b['y'] + b['h']))
            return ratio1 >= ratio or ratio2 >= ratio

    @classmethod
    def get_boxes_of_interval(cls, boxes, interval, direction='', ratio=0.0):
        """ 从boxes中筛选x轴或y轴上interval区间内所有box"""
        # 在direction规定的方向上，有一半在集合内就可以，而不必完全在区间内
        assert direction in ['x', 'y']
        ret = []
        param = 'w' if direction == 'x' else 'h'
        for b in boxes:
            overlap, ratio1, ratio2 = cls.line_overlap((b[direction], b[direction] + b[param]), interval)
            if ratio1 >= ratio or ratio2 >= ratio:
                ret.append(b)
        return ret

    @classmethod
    def boxes_out_boxes(cls, boxes1, boxes2, ratio=0.01, only_check=False):
        """ 检查boxes1中所有不在boxes2的box。ratio越小，对交叉面积要求越低"""
        out_boxes, in_boxes = [], []
        for b1 in boxes1:
            is_in = False
            for b2 in boxes2:
                ratio1 = cls.box_overlap(b1, b2)[1]
                if ratio1 > ratio:  # ratio1指的是交叉面积占b1的比例
                    is_in = True
                    break
            if not is_in:
                out_boxes.append(b1)
                if only_check:
                    return True
            else:
                in_boxes.append(b1)
        return False if only_check else (out_boxes, in_boxes)

    @classmethod
    def horizontal_scan_and_order(cls, boxes, field='', ratio=0.75):
        """ 水平扫描（从右到左，从上到下）boxes并进行排序
        :param boxes: list, 待排序的boxes
        :param field: str, 序号设置在哪个字段
        :param ratio: float, box在x轴的交叉比例超过ratio时，将比较y值。ratio越大，越尊重x值，ratio越小，越照顾y值
        """

        def cmp(a, b):
            x_intersect = cls.is_box_intersected(a, b, direction='x', ratio=ratio)
            if not x_intersect:
                return a['x'] + a['w'] - b['x'] - b['w']
            else:
                return b['y'] - a['y']

        boxes.sort(key=cmp_to_key(cmp), reverse=True)
        for i, box in enumerate(boxes):
            box[field] = i + 1
        return boxes

    @classmethod
    def calc_block_id(cls, blocks):
        """ 计算并设置栏序号，包括block_no/block_id"""
        cls.pop_fields(blocks, ['block_no', 'block_id'])
        cls.horizontal_scan_and_order(blocks, 'block_no')
        for b in blocks:
            b['block_id'] = 'b%s' % b['block_no']
        return blocks

    @classmethod
    def calc_column_id(cls, columns, blocks, auto_filter=False):
        """ 计算和设置列序号，包括column_no/column_id。假定blocks已排好序"""
        cls.pop_fields(columns, ['block_no', 'column_no', 'column_id'])
        for block in blocks:
            block_columns = []
            for c in columns:
                point = c['x'] + c['w'] / 2, c['y'] + c['h'] / 2
                if cls.point_in_box(point, block):
                    c['block_no'] = block['block_no']
                    block_columns.append(c)
            cls.horizontal_scan_and_order(block_columns, 'column_no')
        for i, c in enumerate([c for c in columns if c.get('block_no') is None]):
            c['block_no'] = 0
            c['column_no'] = i + 1
        for c in columns:
            c['column_id'] = 'b%sc%s' % (c['block_no'], c['column_no'])
        if auto_filter:
            return [c for c in columns if c['block_no']]
        else:
            return columns

    @classmethod
    def calc_char_id(cls, chars, columns, small_direction='vertical', auto_filter=False):
        """ 计算字序号，包括char_no/char_id
        :param chars: list, 待排序的chars
        :param columns: list, chars所属的columns。假定已排好序并设置好序号
        :param small_direction: str, 夹注小字的排序规则，vertical表示先下后左，horizontal则表示先左后下
        :param auto_filter: bool, 是否自动过滤掉栏框外的字框和列框、以及列框外的字框
        """

        def pre_params():
            """ 计算char中大框的一般宽度、高度和面积"""
            ws = sorted([c['w'] for c in chars], reverse=True)
            w = ws[2] if len(ws) > 3 else ws[1] if len(ws) > 2 else ws[1]
            hs = sorted([c['h'] for c in chars], reverse=True)
            h = hs[2] if len(hs) > 3 else hs[1] if len(hs) > 2 else hs[1]
            rs = sorted([c['w'] * c['h'] for c in chars], reverse=True)
            a = rs[2] if len(rs) > 3 else rs[1] if len(rs) > 2 else rs[1]
            return w, h, a

        def cmp(a, b):
            """ 从上到下扫描（y轴交叉时，从右到左）时使用"""
            # 尊重y值的大小，ratio值为0.75
            y_intersect = cls.is_box_intersected(a, b, direction='y', ratio=0.75)
            # 并列的夹注小字，在x轴几乎无交叉，ratio设置为0.25
            x_intersect = cls.is_box_intersected(a, b, direction='x', ratio=0.25)
            if y_intersect and not x_intersect:
                return b['x'] - a['x']
            else:
                return a['y'] - b['y']

        def is_big(ch, column=None):
            """ 是否为大字。这里的判断是一定，而不是可能"""
            # 大字很宽或很长，面积不一定很大
            r = (ch['w'] > normal_w * 0.8 or ch['h'] > normal_h * 0.8) and (ch['w'] * ch['h']) > normal_a * 0.8
            if not r and column:
                # 大字很正
                interval = column['x'] + column['w'] * 0.25, column['x'] + column['w'] * 0.75
                o, ratio1, ratio2 = cls.line_overlap(interval, (ch['x'], ch['x'] + ch['w']))
                r = ratio1 > 0.75 and ratio2 > 0.75
            return r

        def is_small(ch, column=None):
            """ 是否为小字。这里的判断是一定，而不是可能"""
            # 小字面积很小，长或宽不一定很短
            r = (ch['w'] < normal_w * 0.5 and ch['h'] < normal_h * 0.5) and (ch['w'] * ch['h']) < normal_a * 0.3
            if not r and column:
                # 小字很偏
                interval = column['x'] + column['w'] * 0.25, column['x'] + column['w'] * 0.75
                o, ratio1, ratio2 = cls.line_overlap(interval, (ch['x'], ch['x'] + ch['w']))
                r = ratio1 < 0.2
            return r

        def maybe_small(ch):
            """ 可能为小字。这里的判断是可能，而不是一定"""
            return ch['w'] < normal_w * 0.75 and ch['h'] < normal_h * 0.75 and (ch['w'] * ch['h']) < normal_a * 0.5

        def set_column_id():
            """ 设置chars的column_no"""
            # 先按中心点落在哪个列框进行分组，设置column_id
            for c in chars:
                # 找到所有交叉的列
                in_columns = [col for col in columns if cls.box_overlap(c, col, True)]
                if not in_columns:
                    # 列框之外的chars统一设置为'b0c0'
                    c['column_id'] = 'b0c0'
                elif len(in_columns) == 1:
                    c['column_id'] = in_columns[0]['column_id']
                else:
                    center = c['x'] + c['w'] / 2, c['y'] + c['h'] / 2
                    for col in in_columns:
                        if cls.point_in_box(center, col):
                            c['column'] = col
                            c['column_id'] = col['column_id']
                        else:
                            c['column_id2'] = col['column_id']
                    if not c.get('column_id'):
                        c['column'] = in_columns[0]
                        c['column_id'] = in_columns[0]['column_id']
                        c['column_id2'] = in_columns[1]['column_id']
            # 然后检查小字落在多个列框的情况，更新column_id
            for c in chars:
                # 检查宽列中小字的情况
                if c.get('column_id2') and c['column']['w'] > normal_w * 0.75 and maybe_small(c):
                    # 检查另一列的情况，是否可移过去
                    col2_chars = [ch for ch in chars if ch.get('column_id') == c.get('column_id2')]
                    col2_neighbors = cls.get_boxes_of_interval(col2_chars, (c['y'], c['y'] + c['h']), 'y', 0.1)
                    col2_top_neighbors = cls.get_boxes_of_interval(col2_chars, (c['y'] - normal_h, c['y']), 'y', 0.1)
                    # 如果另一列有上邻居，且水平邻居为一个小字，则可移过去
                    can_move = col2_top_neighbors and len(col2_neighbors) == 1 and maybe_small(col2_neighbors[0])
                    if can_move:
                        center = c['column']['x'] + c['column']['w'] * 0.5
                        side = 'right' if (c['x'] + c['w'] * 0.5) > center else 'left'
                        col_chars = [ch for ch in chars if ch.get('column_id') == c.get('column_id')]
                        chars_y = sorted([ch['y'] for ch in col_chars])
                        top_neighbors = cls.get_boxes_of_interval(col_chars, (c['y'] - normal_h, c['y']), 'y', 0.1)
                        # 当前不是本列第一个字且上面无字时，尝试移动至另一个列框
                        if (len(col_chars) > 2 and c['y'] > chars_y[1]) and not top_neighbors and can_move:
                            c['column_id'] = c['column_id2']
                        # 小字在右边，但左边是大字
                        elif side == 'right':
                            h_boxes = cls.get_boxes_of_interval(col_chars, (c['y'], c['y'] + c['h']), 'y', 0.1)
                            l_boxes = [b for b in h_boxes if b['x'] < c['x'] and is_big(b)]
                            if l_boxes:
                                c['column_id'] = c['column_id2']
            cls.pop_fields(chars, ['column', 'column_id2'])

        def divide_by_column_id():
            col_chars = dict()
            for c in chars:
                if not col_chars.get(c['column_id']):
                    col_chars[c['column_id']] = []
                col_chars[c['column_id']].append(c)
            if auto_filter:
                col_chars.pop('b0c0', 0)
            return col_chars

        def check_small():
            """ 检查并设置大小字属性"""
            cls.pop_fields(column_chars, 'is_small')
            center = int(column['x']) + int(column['w']) * 0.5
            is_prev_small = False
            while True:
                current_chars = [c for c in column_chars if c.get('is_small') is None]
                if not current_chars:
                    break
                c = current_chars[0]
                # 默认当前节点与前面节点相同
                c['is_small'] = is_prev_small
                h_neighbors = cls.get_boxes_of_interval(column_chars, (c['y'], c['y'] + c['h']), 'y', 0.25)
                if len(h_neighbors) > 1:
                    c['is_small'] = True
                    c['small_side'] = 'right' if (c['x'] + c['w'] * 0.5) > center else 'left'
                else:
                    # 向下找邻居
                    d_neighbors = []
                    down_boxes = [c for c in current_chars if c.get('is_small') is None]
                    if down_boxes:
                        down = down_boxes[0]
                        interval = down['y'], down['y'] + down['h']
                        d_neighbors = cls.get_boxes_of_interval(down_boxes, interval, 'y', 0.25)
                    # 如果当前节点左右无字，下相邻节点左右有字，则当前为大字
                    if len(h_neighbors) == 1 and len(d_neighbors) > 1:
                        c['is_small'] = False
                    # 当前节点和下相邻节点左右均无字，当前判断为大字
                    elif len(h_neighbors) == 1 and len(d_neighbors) == 1 and is_big(c, column):
                        c['is_small'] = False

                if c['is_small']:
                    c['small_side'] = 'right' if (c['x'] + c['w'] * 0.5) > center else 'left'

                # 重置参数
                is_prev_small = c['is_small']

        def scan_and_order():
            """ 针对一列chars排序，其中夹注小字按照先上下后左右的顺序"""
            column_chars.sort(key=cmp_to_key(cmp))
            res, small_list = [], []
            for c in column_chars:
                if not c['is_small']:
                    if not small_list:
                        res.append(c)
                    else:
                        # 从小字切换为大字，则将small_list排序后加入队列
                        res.extend(cls.horizontal_scan_and_order(small_list, 'small_no', 0.5))
                        res.append(c)
                        small_list = []
                else:
                    small_list.append(c)
            if small_list:
                res.extend(cls.horizontal_scan_and_order(small_list, 'small_no', 0.5))
            for i, c in enumerate(res):
                c['char_no'] = i + 1

            return res

        assert chars
        cls.pop_fields(chars, ['block_no', 'column_no', 'char_no', 'column_id'])
        normal_w, normal_h, normal_a = pre_params()

        ret_chars = []
        set_column_id()
        columns_chars = divide_by_column_id()
        for column_id, column_chars in columns_chars.items():
            if column_id == 'b0c0':
                continue
            # 针对每列，从上到下扫描（有交叉时，即小字，从右到左）
            column_chars.sort(key=cmp_to_key(cmp))
            for i, c in enumerate(column_chars):
                c['char_no'] = i + 1
            # 小字的方向为先上下后左右，与前不同
            if small_direction == 'vertical':
                column = [c for c in columns if c['column_id'] == column_id][0]
                check_small()
                column_chars = scan_and_order()
            ret_chars.extend(column_chars)

        for r in ret_chars:
            if r.get('column_id'):
                r['block_no'] = int(r['column_id'][1])
                r['column_no'] = int(r['column_id'][3:])
                r['char_id'] = '%sc%s' % (r['column_id'], r['char_no'])

        return ret_chars

    @classmethod
    def re_calc_id(cls, chars=None, columns=None, blocks=None, page=None, auto_filter=False):
        if not chars and page:
            chars, columns, blocks = page.get('chars') or [], page.get('columns') or [], page.get('blocks') or []
        blocks = cls.calc_block_id(blocks)
        columns = cls.calc_column_id(columns, blocks, auto_filter=auto_filter)
        chars = cls.calc_char_id(chars, columns, auto_filter=auto_filter)
        return blocks, columns, chars

    @classmethod
    def get_chars_col(cls, chars):
        """ 按照column_no对chars分组并设置cid。假定chars已排序"""
        ret = []
        cid_col = []
        for i, c in enumerate(chars):
            column_no1 = c.get('column_no')
            column_no2 = chars[i - 1].get('column_no')
            if i > 1 and column_no1 and column_no2 and column_no1 != column_no2:  # 换行
                ret.append(cid_col)
                cid_col = [c['cid']]
            else:
                cid_col.append(c['cid'])
        if cid_col:
            ret.append(cid_col)
        return ret

    @classmethod
    def update_char_order(cls, chars, chars_col):
        """ 按照chars_col重排chars"""
        for col_no, col in enumerate(chars_col):
            for char_no, cid in enumerate(col):
                cs = [c for c in chars if c['cid'] == cid]
                if cs:
                    c = cs[0]
                    c['column_no'] = col_no + 1
                    c['char_no'] = char_no + 1
                    c['char_id'] = 'b%sc%sc%s' % (c['block_no'], c['column_no'], c['char_no'])
        return sorted(chars, key=itemgetter('block_no', 'column_no', 'char_no'))

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
    def html2txt(cls, html):
        """ 从html中获取txt文本，换行用|、换栏用||表示"""
        txt = ''
        regex1 = re.compile("<ul.*?>.*?</ul>", re.M | re.S)
        regex2 = re.compile("<li.*?>.*?</li>", re.M | re.S)
        for block in regex1.findall(html or ''):
            for line in regex2.findall(block or ''):
                if 'delete' not in line:
                    line_txt = re.sub(r'(<li.*?>|</li>|<span.*?>|</span>|\s)', '', line, flags=re.M | re.S)
                    txt += line_txt + '|'
            txt += '|'
        return re.sub(r'\|{2,}', '||', txt.rstrip('|'))

    @classmethod
    def get_ocr_txt(cls, boxes):
        """ 获取chars或columns里的ocr文本"""
        if not boxes:
            return ''
        pre, txt = boxes[0], ''
        for b in boxes[1:]:
            if pre.get('block_no') and b.get('block_no') and pre['block_no'] != b['block_no']:
                txt += '||'
            elif pre.get('line_no') and b.get('line_no') and pre['line_no'] != b['line_no']:
                txt += '|'
            txt += b.get('ocr_txt', '')
            pre = b
        return txt.strip('|')

    @classmethod
    def check_utf8mb4(cls, seg, base=None):
        column_strip = re.sub(r'\s', '', base or seg.get('base', ''))
        char_codes = [(c, url_escape(c)) for c in list(column_strip)]
        seg['utf8mb4'] = ','.join([c for c, es in char_codes if len(es) > 9])
        return seg

    @staticmethod
    def check_match(chars, txt):
        """ 检查图文是否匹配，包括总行数和每行字数"""
        char_line_num = []
        if chars:
            pre, num = chars[0], 1
            for c in chars[1:]:
                if pre.get('block_no') and c.get('block_no') and pre['block_no'] != c['block_no']:  # 换栏
                    char_line_num.append(num)
                    num = 1
                elif pre.get('line_no') and c.get('line_no') and pre['line_no'] != c['line_no']:  # 换行
                    char_line_num.append(num)
                    num = 1
                else:
                    num += 1
            char_line_num.append(num)

        txt_lines = re.sub(r'[\|\n]+', '|', txt).split('|')
        txt_line_num = [len(line) for line in txt_lines]

        mis_match = []
        if len(char_line_num) < len(txt_line_num):
            for i, num in enumerate(char_line_num):
                if num != txt_line_num[i]:
                    mis_match.append([i, num, txt_line_num[i]])
            for i in range(len(char_line_num), len(txt_line_num)):
                mis_match.append([i, 0, txt_line_num[i]])
        else:
            for i, num in enumerate(txt_line_num):
                if num != char_line_num[i]:
                    mis_match.append([i, char_line_num[i], num])
            for i in range(len(txt_line_num), len(char_line_num)):
                mis_match.append([i, char_line_num[i], 0])

        r = len(char_line_num) == len(txt_line_num) and not mis_match

        return r, mis_match, char_line_num, txt_line_num

    @staticmethod
    def update_chars_txt(chars, txt):
        """ 将txt回写到chars中。假定图文匹配"""
        txt = re.sub(r'[\|\n]+', '', txt)
        if len(chars) != len(txt):
            return False
        for i, c in enumerate(chars):
            c['txt'] = txt[i]
        return chars

    @staticmethod
    def is_box_changed(page_a, page_b, ignore_none=True):
        """ 检查两个页面的切分信息是否发生了修改"""
        for field in ['blocks', 'columns', 'chars']:
            a, b = page_a.get(field), page_b.get(field)
            if ignore_none and (not a or not b):
                continue
            if len(a) != len(b):
                return field + '.len'
            for i in range(len(a)):
                for j in ['x', 'y', 'w', 'h']:
                    if abs(a[i][j] - b[i][j]) > 0.1 and (field != 'blocks' or len(a) > 1):
                        return '%s[%d] %s %f != %f' % (field, i, j, a[i][j], b[i][j])

    @classmethod
    def diff(cls, base, cmp1='', cmp2='', cmp3=''):
        """ 生成文字校对的segment"""
        # 1. 生成segments
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
        # 2. 结构化，以便页面输出
        blocks = {}
        for s in segments:
            b_no, l_no = s['block_no'], s['line_no']
            if not blocks.get(b_no):
                blocks[b_no] = {}
            if not blocks[b_no].get(l_no):
                blocks[b_no][l_no] = []
            if not (s['is_same'] and s['base'] == '\n'):
                s['offset'] = s['range'][0]
                blocks[b_no][l_no].append(s)
        return blocks

    @staticmethod
    def merge_narrow_columns(columns):
        """ 合并窄列"""
        if len(columns) < 3:
            return columns
        ws = sorted([c['w'] for c in columns], reverse=True)
        max_w = ws[0] * 1.1
        threshold = ws[2] * 0.75
        ret_columns = [columns[0]]
        for cur in columns[1:]:
            last = ret_columns[-1]
            x, w = cur['x'], last['x'] + last['w'] - cur['x']
            b_cur, b_last = cur.get('block_no', 0), last.get('block_no', 0)
            if b_cur == b_last and w < max_w and cur['w'] < threshold and last['w'] < threshold:
                y = min([cur['y'], last['y']])
                h = max([cur['y'] + cur['h'], last['y'] + last['h']]) - y
                ret_columns[-1].update(dict(x=round(x, 2), y=round(y, 2), w=round(w, 2), h=round(h, 2)))
            else:
                ret_columns.append(cur)
        return ret_columns

    @classmethod
    def deduplicate_columns(cls, columns):
        """ 删除冗余的列"""
        if len(columns) < 3:
            return columns
        ws = sorted([c['w'] for c in columns], reverse=True)
        threshold = ws[2] * 0.75
        ret_columns = [columns[0]]
        for cur in columns[1:]:
            last = ret_columns[-1]
            overlap, ratio1, ratio2 = cls.box_overlap(last, cur)
            # 检查上一个字框，如果是窄框且重复度超过0.45，或者是大框且重复度超过0.55时，都将去除
            if (last['w'] < threshold and ratio1 > 0.45) or (last['w'] >= threshold and ratio1 > 0.55):
                ret_columns.pop()
            # 检查当前字框
            if (cur['w'] < threshold and ratio2 < 0.45) or (cur['w'] >= threshold and ratio2 < 0.55):
                ret_columns.append(cur)
        return ret_columns
