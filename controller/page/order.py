#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 字框工具
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

    @staticmethod
    def is_point_in_box(point, box):
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

    @classmethod
    def get_cast_length(cls, boxes, interval, direction='x'):
        """ 获取boxes在x轴或y轴方向、区间interval内的投影长度"""

        def get_length(b):
            if direction == 'x':
                return cls.line_overlap((b['x'], b['x'] + b['w']), interval)[0]
            else:
                return cls.line_overlap((b['y'], b['y'] + b['h']), interval)[0]

        return sum([get_length(b) for b in boxes])

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
    def get_boxes_of_interval(cls, boxes, interval, direction='', ratio=0.0, op='or'):
        """ 从boxes中筛选x轴或y轴上interval区间内所有box"""
        assert direction in ['x', 'y']
        ret = []
        param = 'w' if direction == 'x' else 'h'
        for b in boxes:
            overlap, ratio1, ratio2 = cls.line_overlap((b[direction], b[direction] + b[param]), interval)
            if op == 'and' and (ratio1 >= ratio and ratio2 >= ratio):
                ret.append(b)
            elif ratio1 >= ratio or ratio2 >= ratio:
                ret.append(b)
        return ret

    @classmethod
    def get_boxes_of_region(cls, boxes, region, ratio=0.0):
        """ 从boxes中筛选region范围内的所有box"""
        ret = []
        for b in boxes:
            ratio1 = cls.box_overlap(b, region)[1]
            if ratio1 >= ratio:
                ret.append(b)
        return ret

    @classmethod
    def get_outer_range(cls, boxes):
        """ 获取boxes的外包络框"""
        x = sorted([b['x'] for b in boxes])[0]
        y = sorted([b['y'] for b in boxes])[0]
        w = sorted([b['x'] + b['w'] for b in boxes])[-1] - x
        h = sorted([b['y'] + b['h'] for b in boxes])[-1] - y
        return dict(x=x, y=y, w=w, h=h)

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
    def horizontal_scan_and_order(cls, boxes, field='', ratio=0.75):
        """ 水平扫描（从右到左扫描，如果上下交叉，则从上到下）boxes并进行排序
        :param boxes: list, 待排序的boxes
        :param field: str, 序号设置在哪个字段
        :param ratio: float, 上下交叉比例超过ratio时，将比较y值
        """

        def cmp(a, b):
            r1, r2 = cls.get_box_overlap(a, b, direction='x')[1:]
            if r1 < ratio and r2 < ratio:
                return a['x'] + a['w'] - b['x'] - b['w']
            else:
                return b['y'] - a['y']

        boxes.sort(key=cmp_to_key(cmp), reverse=True)
        if field:
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
    def calc_column_id(cls, columns, blocks):
        """ 计算和设置列序号，包括column_no/column_id。假定blocks已排好序"""
        cls.pop_fields(columns, ['block_no', 'column_no', 'column_id'])
        for block in blocks:
            block_columns = []
            for c in columns:
                point = c['x'] + c['w'] / 2, c['y'] + c['h'] / 2
                if cls.is_point_in_box(point, block):
                    c['block_no'] = block['block_no']
                    block_columns.append(c)
            cls.horizontal_scan_and_order(block_columns, 'column_no')
        for i, c in enumerate([c for c in columns if c.get('block_no') is None]):
            c['block_no'] = 0
            c['column_no'] = i + 1
        for c in columns:
            c['column_id'] = 'b%sc%s' % (c['block_no'], c['column_no'])
        return columns

    @classmethod
    def scan_small_and_order(cls, boxes, field='small_no'):
        """ 扫描小字列并排序。算法会从右上角第一个框开始往下找，找完该列后，又从剩下的框中右上角的第一个节点往下找。
        :param boxes: list, 待排序的boxes
        :param field: str, 序号设置在哪个字段
        """

        def find_next():
            left_boxes = [b for b in boxes if not b.get(field)]
            if not left_boxes:
                return None
            ud_neighbors = cls.get_boxes_of_interval(left_boxes, (cur['x'], cur['x'] + cur['w']), 'x', 0.5)
            dn_neighbors = [c for c in ud_neighbors if c['y'] > cur['y'] + cur['h']]
            if dn_neighbors:
                dn_neighbors.sort(key=itemgetter('y'))
                return dn_neighbors[0]
            else:
                return left_boxes[0]

        cls.horizontal_scan_and_order(boxes, ratio=0.4)
        cur, no = boxes[0], 2
        cur[field] = 1
        while True:
            nex = find_next()
            if not nex:
                break
            nex[field] = no
            cur = nex
            no += 1

    @classmethod
    def calc_char_id(cls, chars, columns, detect_col=True, small_direction='down'):
        """ 针对字框排序，并设置char_no/char_id等序号
        :param chars: list, 待排序的字框
        :param columns: list, 字框所在的列，假定已排序并设置序号
        :param detect_col: bool, 当字框属于多列时，是否自适应的检测和调整
        :param small_direction: str, 下一个夹注小字的方向，down表示往下找，left表示往左找
        """

        def cmp(a, b):
            """ 从上到下扫描（如果左右交叉时，则从右到左）"""
            ry1, ry2 = cls.get_box_overlap(a, b, 'y')[1:]
            rx1, rx2 = cls.get_box_overlap(a, b, 'x')[1:]
            if (ry1 > 0.75 or ry2 > 0.75) and (rx1 < 0.25 and rx2 < 0.25):
                return b['x'] - a['x']
            else:
                return a['y'] - b['y']

        def get_column(col_id):
            cols = [c for c in columns if c['column_id'] == col_id]
            return cols and cols[0]

        def is_narrow_column(col):
            return col['w'] <= normal_w * 0.6

        def params():
            """ 计算正常字框的宽度、高度和面积"""
            wc = sorted([c['w'] for c in chars], reverse=True)
            big_w = wc[2] if len(wc) > 3 else wc[1] if len(wc) > 2 else wc[1]
            normal_chars = [c for c in chars if c['w'] > big_w * 0.75]
            ws = [c['w'] for c in normal_chars]
            w = round(sum(ws) / len(ws), 2)
            hs = [c['h'] for c in normal_chars]
            h = round(sum(hs) / len(hs), 2)
            rs = [c['w'] * c['h'] for c in normal_chars]
            r = round(sum(rs) / len(rs), 2)
            return w, h, r

        def set_properties():
            """ 设置column_id以及各种属性"""
            # 初步检查、设置参数
            for c in chars:
                r = c['w'] / normal_w
                a = c['w'] * c['h'] / normal_a
                c['size'] = 'big' if r > 0.85 or a > 0.75 else 'small' if r < 0.6 or a < 0.45 else 'median'
                in_columns = [col for col in columns if cls.box_overlap(c, col, True)]
                if not in_columns:
                    c['column_id'] = 'b0c0'
                elif len(in_columns) == 1:
                    c['column'] = in_columns[0]
                    c['column_id'] = c['column']['column_id']
                else:
                    # 字框在多列时，根据字框面积主要落在哪列设置column_id，另一列设置为column_id2
                    in_columns = [(cls.box_overlap(c, col)[1], col) for col in in_columns]
                    in_columns.sort(key=itemgetter(0))
                    c['column'] = in_columns[-1][1]
                    c['column_id'] = c['column']['column_id']
                    c['column2'] = in_columns[0][1]
                    c['column_id2'] = c['column2']['column_id']

            # 检查、调整小字字框落在多列的情况
            if detect_col:
                for c in chars:
                    if c.get('column_id2') and not is_narrow_column(c['column']) and c['size'] == 'small':
                        # 检查c在两列的水平邻居
                        x = min(c['column']['x'], c['column2']['x'])
                        w = max(c['column']['x'] + c['column']['w'], c['column2']['x'] + c['column2']['w']) - x
                        hr_neighbors = cls.get_boxes_of_region(chars, dict(x=x, y=c['y'], w=w, h=c['h']), 0.25)
                        hr_neighbors1 = [ch for ch in hr_neighbors if ch['column_id'] == c['column_id']]
                        hr_neighbors2 = [ch for ch in hr_neighbors if ch['column_id'] == c['column_id2']]
                        big1 = [c['column_id'] for c in hr_neighbors1 if c['size'] == 'big']
                        big2 = [c['column_id'] for c in hr_neighbors2 if c['size'] == 'big']
                        # 如果另一列有两个字或有大字
                        if len(hr_neighbors2) >= 2 or len(big2) >= 1:
                            continue
                        # 如果本列包括自己超过三个字或有大字
                        if len(hr_neighbors1) > 3 or len(big1) >= 1:
                            c['column_id'] = c['column_id2']
                            continue
                        # 如果有上邻居，就随上邻居
                        region = dict(x=c['x'], y=c['y'] - normal_h, w=c['w'], h=normal_h)
                        up_neighbors = cls.get_boxes_of_region(chars, region, 0.1)
                        up_neighbors = [ch for ch in up_neighbors if c['y'] - ch['y'] - ch['h'] > 0]
                        up_neighbors = [(cls.box_overlap(region, ch)[1], ch) for ch in up_neighbors]
                        up_neighbors.sort(key=itemgetter(0))
                        if up_neighbors and c['column_id'] != up_neighbors[-1][1]['column_id']:
                            c['column_id'] = c['column_id2']

            # 根据column_id分组
            cols_chars = OrderedDict()
            for c in chars:
                col_id = c['column_id']
                cols_chars[col_id] = cols_chars[col_id] if cols_chars.get(col_id) else []
                cols_chars[col_id].append(c)

            # 设置y_overlap参数
            for col_id, col_chars in cols_chars.items():
                for i, c in enumerate(col_chars):
                    y_cast_length = cls.get_cast_length(col_chars, (c['y'], c['y'] + c['h']), 'y')
                    c['y_overlap'] = (y_cast_length - c['h']) / c['h']

            # 初步设置side参数
            for col_id, col_chars in cols_chars.items():
                if col_id != 'b0c0':
                    col = get_column(col_id)
                    for i, c in enumerate(col_chars):
                        cen_line = col['x'] + col['w'] * 0.5
                        c['side'] = 'left' if c['x'] + c['w'] * 0.5 < cen_line else 'right'
                        cen_interval = col['x'] + col['w'] * 0.25, col['x'] + col['w'] * 0.75
                        r1, r2 = cls.line_overlap(cen_interval, (c['x'], c['x'] + c['w']))[1:]
                        if r1 > 0.9 or r2 > 0.99 or (r1 > 0.85 and r2 > 0.85) or (r1 > 0.80 and r2 > 0.9):
                            c['side'] = 'center'

            # 针对独立小字，根据它之前的字框来调整，以适应列倾斜的情况
            for col_id, col_chars in cols_chars.items():
                if col_id != 'b0c0':
                    col = get_column(col_id)
                    for i, c in enumerate(col_chars):
                        if c['size'] == 'small' and c['y_overlap'] < 0.25:
                            region = dict(x=col['x'], y=c['y'] - normal_h / 2, w=col['w'], h=normal_h / 2)
                            up_neighbors = cls.get_boxes_of_region(col_chars, region, 0.25)
                            if up_neighbors and (len(up_neighbors) > 1 or up_neighbors[0]['side'] == 'center'):
                                up_range = cls.get_outer_range(up_neighbors)
                                interval = up_range['x'] + up_range['w'] * 0.25, up_range['x'] + up_range['w'] * 0.75
                                r1, r2 = cls.line_overlap(interval, (c['x'], c['x'] + c['w']))[1:]
                                if r1 > 0.9 or (r1 > 0.85 and r2 > 0.85):
                                    c['side'] = 'center'

            return cols_chars

        def check_small_note():
            """ 检查字框是否为夹注小字"""
            for col_id, col_chars in columns_chars.items():
                if col_id == 'b0c0':
                    continue

                col = get_column(col_id)
                if is_narrow_column(col):
                    cls.set_field(col_chars, 'is_small', True)
                    continue

                for i, c in enumerate(col_chars):
                    c['is_small'] = None
                    if c['size'] == 'big' and c['side'] != 'right' and c['y_overlap'] < 0.25:
                        c['is_small'] = False
                    elif c['size'] == 'median' and c['side'] != 'right' and c['y_overlap'] < 0.15:
                        c['is_small'] = False
                    elif c['size'] == 'small' and c['side'] == 'center' and c['y_overlap'] < 0.1:
                        region = dict(x=col['x'], y=c['y'] - normal_h / 2, w=col['w'], h=normal_h / 2)
                        up_neighbors = cls.get_boxes_of_region(col_chars, region, 0.25)
                        sm_neighbors = [c for c in up_neighbors if c['size'] != 'big']
                        if not up_neighbors or len(sm_neighbors) == 2:
                            c['is_small'] = False
                        elif len(up_neighbors) == 1 and up_neighbors[0]['is_small'] is False:
                            c['is_small'] = False

        def scan_and_order():
            """ 针对每列字框从上到下排序，针对连续的夹注小字时，先分列，列内上下排序，列间左右排序"""
            for col_id, col_chars in columns_chars.items():
                if col_id == 'b0c0':
                    cls.horizontal_scan_and_order(col_chars, 'char_no', 0.6)
                    continue

                col = get_column(col_id)
                if is_narrow_column(col):
                    cls.horizontal_scan_and_order(col_chars, 'char_no', 0.6)
                    continue

                ordered_chars, small_list = [], []
                for c in col_chars:
                    if c['is_small'] is not False:
                        small_list.append(c)
                    else:
                        if not small_list:  # 连续的大字
                            ordered_chars.append(c)
                        else:  # 从小字切换为大字
                            cls.scan_small_and_order(small_list)
                            ordered_chars.extend(small_list)
                            ordered_chars.append(c)
                            small_list = []
                if small_list:
                    cls.scan_small_and_order(small_list)
                    ordered_chars.extend(small_list)

                for i, c in enumerate(ordered_chars):
                    c['char_no'] = i + 1

                columns_chars[col_id] = ordered_chars

        assert chars
        assert small_direction in ['down', 'left']
        cls.pop_fields(chars, 'column,column2,column_id,column_id2,side,y_overlap,size,is_small')

        normal_w, normal_h, normal_a = params()
        columns_chars = set_properties()
        for column_id, column_chars in columns_chars.items():
            column_chars.sort(key=cmp_to_key(cmp))
            for i, c in enumerate(column_chars):
                c['char_no'] = i + 1
        if small_direction == 'down':
            check_small_note()
            scan_and_order()

        ret_chars = []
        for column_id, column_chars in columns_chars.items():
            for c in column_chars:
                c['block_no'] = int(c['column_id'][1])
                c['column_no'] = int(c['column_id'][3:])
                c['char_id'] = '%sc%s' % (c['column_id'], c['char_no'])
            ret_chars.extend(column_chars)

        cls.pop_fields(ret_chars, 'column,column2,column_id,column_id2,side,y_overlap')
        return ret_chars
