#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 字序工具
@time: 2019/6/3
"""
from operator import itemgetter
from functools import cmp_to_key
from collections import OrderedDict


class BoxOrder(object):

    @staticmethod
    def pop_fields(boxes, fields):
        assert type(fields) in [str, list]
        fields = fields.replace(' ', '').split(',') if isinstance(fields, str) else fields
        for b in boxes:
            for field in fields:
                b.pop(field, 0)
        return boxes

    @staticmethod
    def set_field(boxes, field, value):
        for b in boxes:
            b[field] = value
        return boxes

    @classmethod
    def get_outer_range(cls, boxes):
        """ 获取boxes的外包络框"""
        x = sorted([b['x'] for b in boxes])[0]
        y = sorted([b['y'] for b in boxes])[0]
        w = sorted([b['x'] + b['w'] for b in boxes])[-1] - x
        h = sorted([b['y'] + b['h'] for b in boxes])[-1] - y
        return dict(x=x, y=y, w=w, h=h)

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
        """ 计算两个框的交叉面积和比例。如果only_check为True，则只要交叉就返回True"""
        x1, y1, w1, h1 = box1['x'], box1['y'], box1['w'], box1['h']
        x2, y2, w2, h2 = box2['x'], box2['y'], box2['w'], box2['h']
        if x1 > x2 + w2 or x2 > x1 + w1 or y1 > y2 + h2 or y2 > y1 + h1:
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
    def get_box_overlap(cls, a, b, direction=''):
        if not direction:
            return cls.box_overlap(a, b)
        elif direction == 'x':
            return cls.line_overlap((a['x'], a['x'] + a['w']), (b['x'], b['x'] + b['w']))
        elif direction == 'y':
            return cls.line_overlap((a['y'], a['y'] + a['h']), (b['y'], b['y'] + b['h']))

    @classmethod
    def get_boxes_of_region(cls, boxes, region, ratio=0.0, set_ratio=False):
        """ 从boxes中筛选region范围内的所有box"""
        ret = []
        for b in boxes:
            ratio1 = cls.box_overlap(b, region)[1]
            if ratio1 >= ratio:
                ret.append(b)
                if set_ratio:
                    b['ratio'] = ratio1
        return ret

    @classmethod
    def boxes_out_of_boxes(cls, boxes1, boxes2, ratio=0.01, only_check=False):
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
    def cmp_up2down(cls, a, b):
        """ 从上到下扫描（如果左右交叉时，则从右到左）"""
        ry1, ry2 = cls.get_box_overlap(a, b, 'y')[1:]
        rx1, rx2 = cls.get_box_overlap(a, b, 'x')[1:]
        # 当二者在y轴上交叉且x轴几乎不交叉时，认为二者是水平邻居，则从右到左，即x值大的在前
        if (ry1 > 0.5 or ry2 > 0.5) and (ry1 > 0.25 or ry2 > 0.25) and (rx1 < 0.25 and rx2 < 0.25):
            return b['x'] - a['x']
        # 否则，从上到下，即y值小的在前
        else:
            return a['y'] - b['y']

    @classmethod
    def cmp_right2left(cls, a, b):
        """ 从右到左扫描（如果上下交叉时，则从上到下）"""
        ry1, ry2 = cls.get_box_overlap(a, b, 'y')[1:]
        rx1, rx2 = cls.get_box_overlap(a, b, 'x')[1:]
        # 当二者在x轴上交叉且y轴几乎不交叉时，认为二者是上下邻居，则从上到下，即y值小的在前
        if (rx1 > 0.5 or rx2 > 0.5) and (rx1 > 0.25 and rx2 > 0.25) and (ry1 < 0.25 and ry2 < 0.25):
            return a['y'] - b['y']
        # 否则，从右到左，即x值大的在前
        else:
            return b['x'] - a['x']

    @classmethod
    def calc_block_id(cls, blocks):
        """ 计算并设置栏序号，包括block_no/block_id"""
        cls.pop_fields(blocks, ['block_no', 'block_id'])
        blocks.sort(key=cmp_to_key(cls.cmp_up2down))
        for i, b in enumerate(blocks):
            b['block_no'] = i + 1
            b['block_id'] = 'b%s' % (i + 1)
        return blocks

    @classmethod
    def calc_column_id(cls, columns, blocks):
        """ 计算和设置列序号，包括column_no/column_id。假定blocks已排好序"""
        cls.pop_fields(columns, ['block_no', 'column_no', 'column_id'])
        # 设置栏号
        for c in columns:
            in_blocks = [(cls.box_overlap(c, b)[1], b) for b in blocks if cls.box_overlap(c, b)[1] > 0]
            if in_blocks:
                in_block = sorted(in_blocks, key=itemgetter(0), reverse=True)[0][1]
                c['block_no'] = in_block['block_no']
        # 按栏分列
        in_columns = []
        for b in blocks:
            b_columns = [c for c in columns if c.get('block_no') == b['block_no']]
            b_columns.sort(key=cmp_to_key(cls.cmp_right2left))
            for i, c in enumerate(b_columns):
                c['column_no'] = i + 1
            in_columns.extend(b_columns)
        # 栏外的列
        out_columns = [c for c in columns if c.get('block_no') is None]
        for i, c in enumerate(out_columns):
            c['block_no'] = 0
            c['column_no'] = i + 1
        # 设置返回
        ret = out_columns + in_columns
        for c in ret:
            c['column_id'] = 'b%sc%s' % (c['block_no'], c['column_no'])
        return ret

    @classmethod
    def calc_char_id(cls, chars, columns, detect_col=True, small_direction='down'):
        """ 针对字框排序，并设置char_no/char_id等序号
        :param chars: list, 待排序的字框
        :param columns: list, 字框所在的列，假定已排序并设置序号
        :param detect_col: bool, 当字框属于多列时，是否自适应的检测和调整
        :param small_direction: str, 下一个夹注小字的方向，down表示往下找，left表示往左找
        """

        def cmp_small(a, b):
            side2int = dict(left=3, center=2, right=1)
            if a['side'] != b['side']:
                return side2int.get(a['side']) - side2int.get(b['side'])
            else:
                return a['y'] - b['y']

        def is_narrow_column(col_id):
            return column_dict.get(col_id)['w'] <= nm_cl_w * 0.6

        def is_hr_neighbor(a, b):
            ry1, ry2 = cls.get_box_overlap(a, b, 'y')[1:]
            rx1, rx2 = cls.get_box_overlap(a, b, 'x')[1:]
            # 二者在y轴有交叉，x轴交叉不大，则认为是水平邻居
            if (ry1 > 0.25 or ry2 > 0.25) and (rx1 < 0.25 and rx2 < 0.25):
                return True

        def init_params():
            # 计算正常字框的宽度、高度和面积
            ch = sorted([c['w'] for c in chars], reverse=True)
            big_ch = ch[2] if len(ch) > 3 else ch[1] if len(ch) > 2 else ch[1] if len(ch) > 1 else ch[0]
            normal_chars = [c for c in chars if big_ch * 0.75 < c['w'] <= big_ch]
            ch_ws = [c['w'] for c in normal_chars]
            ch_w = round(sum(ch_ws) / len(ch_ws), 2)
            ch_hs = [c['h'] for c in normal_chars]
            ch_h = round(sum(ch_hs) / len(ch_hs), 2)
            ch_as = [c['w'] * c['h'] for c in normal_chars]
            ch_a = round(sum(ch_as) / len(ch_as), 2)
            # 计算正常列框的宽度
            cl = sorted([c['w'] for c in columns], reverse=True)
            big_cl = cl[2] if len(cl) > 3 else cl[1] if len(cl) > 2 else cl[1] if len(cl) > 1 else cl[0]
            normal_columns = [c for c in columns if big_cl * 0.75 < c['w'] <= big_cl]
            cl_ws = [c['w'] for c in normal_columns]
            cl_w = round(sum(cl_ws) / len(cl_ws), 2)
            return ch_w, ch_h, ch_a, cl_w

        def get_side_and_ratio(ch, col_chars, col_range):
            """ 计算字框的位置和列宽的占比"""
            nb_chars = [(c, abs(c['y'] - ch['y'])) for c in col_chars if c['hr_nbs']]
            if nb_chars:  # 先以最近的并排夹注小字的作为参照
                nb_ch = sorted(nb_chars, key=itemgetter(1))[0][0]
                out_range = cls.get_outer_range(nb_ch['hr_nbs'] + [nb_ch])
            else:  # 次以整列的外包络作为参照
                out_range = col_range
            r_w = cls.line_overlap((out_range['x'], out_range['x'] + out_range['w']), (ch['x'], ch['x'] + ch['w']))[1]
            cen_line = out_range['x'] + out_range['w'] * 0.5
            ch['side'] = 'left' if ch['x'] + ch['w'] * 0.5 < cen_line else 'right'
            cen_interval = out_range['x'] + out_range['w'] * 0.25, out_range['x'] + out_range['w'] * 0.75
            r1, r2 = cls.line_overlap(cen_interval, (ch['x'], ch['x'] + ch['w']))[1:]
            if r2 > 0.99 or r1 > 0.99 or (r1 > 0.8 and r1 + r2 > 1.6):
                ch['side'] = 'center'
            return ch['side'], r_w

        def set_column_id():
            # 初步设置column_id和size参数
            for c in chars:
                r = c['w'] / nm_ch_w
                a = (c['w'] * c['h']) / nm_ch_a
                c['size'] = 'big' if r > 0.85 and a > 0.65 else 'small' if r < 0.55 and a < 0.35 else 'median'
                in_columns = [col for col in columns if cls.box_overlap(c, col)[1] > 0.25]
                if not in_columns:
                    c['column_id'] = 'b0c0'
                elif len(in_columns) == 1:
                    c['column_id'] = in_columns[0]['column_id']
                else:
                    # 字框在多列时，根据字框面积主要落在哪列设置column_id
                    in_columns = [(cls.box_overlap(c, col)[1], col) for col in in_columns]
                    in_columns.sort(key=itemgetter(0), reverse=True)
                    c['column_id'] = in_columns[0][1]['column_id']
                    c['column_id2'] = in_columns[1][1]['column_id']

            # 进一步调整字框落在多列的情况
            if detect_col:
                for c in chars:
                    if c.get('column_id2') and not is_narrow_column(c['column_id']) and c['size'] != 'big':
                        # 如果有上邻居，就随上邻居
                        region = dict(x=c['x'], y=c['y'] - nm_ch_h, w=c['w'], h=nm_ch_h)
                        up_nbs = cls.get_boxes_of_region(chars, region, 0.1, set_ratio=True)
                        up_nbs = [ch for ch in up_nbs if c['y'] > ch['y'] and cls.get_box_overlap(c, ch, 'x')[1] > 0.5]
                        if up_nbs:
                            up_nbs.sort(key=itemgetter('ratio'))
                            c['column_id'] = up_nbs[-1]['column_id']
                            cls.pop_fields(up_nbs, 'ratio')
                            continue
                        # 没有上邻居，就检查两列的水平邻居
                        column1 = column_dict.get(c['column_id'])
                        column2 = column_dict.get(c['column_id2'])
                        x = min(column1['x'], column2['x'])
                        w = max(column1['x'] + column1['w'], column2['x'] + column2['w']) - x
                        hr_nbs = cls.get_boxes_of_region(chars, dict(x=x, y=c['y'], w=w, h=c['h']), 0.1)
                        hr_nbs2 = [ch for ch in hr_nbs if ch['column_id'] == c['column_id2']]
                        hr_nbs1 = [ch for ch in hr_nbs if ch['column_id'] == c['column_id']]
                        # 比较把c放过去之后两列的水平宽度
                        hr_w1 = cls.get_outer_range(hr_nbs1)['w']
                        hr_w2 = cls.get_outer_range(hr_nbs2 + [c])['w']
                        # 如果放在另一列的宽度更窄，则移过去
                        if hr_w2 < hr_w1:
                            c['column_id'] = c['column_id2']

            # 根据column_id分组
            cols_chars = OrderedDict()
            for c in chars:
                col_id = c['column_id']
                cols_chars[col_id] = cols_chars[col_id] if cols_chars.get(col_id) else []
                cols_chars[col_id].append(c)

            return cols_chars

        def scan_and_order():
            # 检查是否为b0c0或是窄列
            if column_id == 'b0c0' or is_narrow_column(column_id):
                column_chars.sort(key=cmp_to_key(cls.cmp_up2down))
                for i, c in enumerate(column_chars):
                    c['char_no'] = i + 1
                return

            # 初步检查、设置字框的水平邻居
            col_len = len(column_chars)
            for i, c in enumerate(column_chars):
                c['hr_nbs'] = c['hr_nbs'] if c.get('hr_nbs') else []
                for j in range(1, 5):  # 往后找4个节点
                    n = column_chars[i + j] if i < col_len - j else {}
                    if n and is_hr_neighbor(c, n):
                        n['hr_nbs'] = n['hr_nbs'] if n.get('hr_nbs') else []
                        c['hr_nbs'].append(n)
                        n['hr_nbs'].append(c)

            # 进一步检查水平邻居中的上下关系
            for i, c in enumerate(column_chars):
                hr_nbs = c['hr_nbs']
                if not hr_nbs or len(hr_nbs) < 2:
                    continue
                res_nbs, handled = [], []
                for b in hr_nbs:
                    if b['cid'] not in handled:
                        # 从所有水平邻居中找出和b有上下关系的节点
                        dup_nbs = [n for n in hr_nbs if cls.get_box_overlap(b, n, 'x')[1] > 0.25]
                        # 从上下关系的节点中选择和c在y轴上重复度最大的节点
                        nb = sorted([(cls.get_box_overlap(c, n, 'y')[1], n) for n in dup_nbs], key=itemgetter(0))[-1]
                        res_nbs.append(nb[1])
                        handled.extend([n['cid'] for n in dup_nbs])
                c['hr_nbs'] = res_nbs

            # 检查最多的水平邻居数，以此判断是否有小字以及小字的列数
            max_nb_cnt = max([len(c.get('hr_nbs') or []) for c in column_chars])
            if max_nb_cnt == 0:  # 整列无水平邻居，则直接排序、返回
                column_chars.sort(key=cmp_to_key(cls.cmp_up2down))
                for i, c in enumerate(column_chars):
                    c['char_no'] = i + 1
                return

            # 检查、设置是否夹注小字
            col_range = cls.get_outer_range(column_chars)
            for c in column_chars:
                if c['hr_nbs']:
                    c['is_small'] = True
                    continue
                if c['size'] == 'big':
                    c['is_small'] = False
                    continue
                side, r_w = get_side_and_ratio(c, column_chars, col_range)  # r_w为字宽占附近列宽的比例
                if side == 'center':
                    if r_w > 0.6 or c['size'] == 'median':
                        c['is_small'] = False
                    else:  # 居中小字
                        c['is_small'] = True
                        # 如果下邻居也无左右邻居且大小和位置跟自己差不多，则是连续的非夹注小字
                        dn_region = dict(x=c['x'], y=c['y'] + c['h'], w=c['w'], h=nm_ch_h)
                        dn_nbs = cls.get_boxes_of_region(column_chars, dn_region, 0.25)
                        if dn_nbs:
                            dnb = sorted(dn_nbs, key=itemgetter('y'))[0]
                            n_side, r_n = get_side_and_ratio(dnb, column_chars, col_range)
                            if not dnb['hr_nbs'] and n_side == 'center' and r_n < 0.6:
                                c['is_small'] = False
                else:
                    if r_w > 0.75:
                        c['is_small'] = False
                    elif r_w < 0.5:
                        c['is_small'] = True
                    else:  # 不居中的中号字
                        c['is_small'] = True
                        up_region = dict(x=c['x'], y=c['y'] - nm_ch_h, w=c['w'], h=nm_ch_h)
                        up_nbs = cls.get_boxes_of_region(column_chars, up_region, 0.25)
                        if up_nbs:  # 随上邻居
                            unb = sorted(up_nbs, key=itemgetter('y'))[-1]
                            c['is_small'] = unb['is_small']

            # 检查、设置左右位置，以便排序
            for c in column_chars:
                if c['is_small'] and not c.get('side'):
                    get_side_and_ratio(c, column_chars, col_range)

            # 针对连续的夹注小字重新排序
            small_start = None
            for i, c in enumerate(column_chars):
                if c['is_small']:
                    if small_start is None:
                        small_start = i
                    nex = column_chars[i + 1] if i < len(column_chars) - 1 else {}
                    if not nex.get('is_small') or not nex:
                        if max_nb_cnt == 1 and i - small_start >= 5:
                            ordered = sorted(column_chars[small_start: i + 1], key=cmp_to_key(cmp_small))
                        else:
                            ordered = sorted(column_chars[small_start: i + 1], key=cmp_to_key(cls.cmp_right2left))
                        column_chars[small_start: i + 1] = ordered
                        small_start = None

        assert chars
        assert small_direction in [None, '', 'down', 'left']
        small_direction = 'down' if not small_direction else small_direction
        cls.pop_fields(chars, 'column_id,column_id2,char_no,hr_nbs,side,size,is_small')

        ret_chars = []
        column_dict = {c['column_id']: c for c in columns}
        nm_ch_w, nm_ch_h, nm_ch_a, nm_cl_w = init_params()
        columns_chars = set_column_id()
        for column_id, column_chars in columns_chars.items():
            column_chars.sort(key=cmp_to_key(cls.cmp_up2down))
            if small_direction == 'down':
                scan_and_order()
            for i, c in enumerate(column_chars):
                c['char_no'] = i + 1
                c['block_no'] = int(column_id[1])
                c['column_no'] = int(column_id[3:])
                c['char_id'] = '%sc%s' % (column_id, i + 1)
            ret_chars.extend(column_chars)

        cls.pop_fields(ret_chars, 'column_id,column_id2,hr_nbs,side')
        return ret_chars
