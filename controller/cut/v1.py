#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 计算字序
@time: 2019/10/16
"""

import os
import sys

sys.path.append(os.path.dirname(__file__))


def calc_order(char_list, indices):
    """计算字序"""
    candidates = [{'ch_id': 0, 'sub_col_id': 1, 'note_id': 1}, {'ch_id': 1, 'sub_col_id': 0, 'note_id': 0}]
    for order in range(0, len(indices)):
        flag = 0
        for d in candidates:
            for i in indices:
                c = char_list[i]
                if c['ch_id'] == d['ch_id'] and c['sub_col_id'] == d['sub_col_id'] and c['note_id'] == d['note_id']:
                    flag = 1
                    c['column_order'] = order + 1
                    if d['sub_col_id'] != 0:
                        # 这个字是小字
                        candidates = [{'ch_id': c['ch_id'], 'sub_col_id': c['sub_col_id'],
                                       'note_id': c['note_id'] + 1},
                                      {'ch_id': c['ch_id'], 'sub_col_id': c['sub_col_id'] + 1,
                                       'note_id': 1},
                                      {'ch_id': c['ch_id'] + 1, 'sub_col_id': 0, 'note_id': 0},
                                      {'ch_id': c['ch_id'] + 1, 'sub_col_id': 1, 'note_id': 1}]
                    else:
                        candidates = [{'ch_id': c['ch_id'], 'sub_col_id': 1, 'note_id': 1},
                                      {'ch_id': c['ch_id'] + 1, 'sub_col_id': 0, 'note_id': 0},
                                      {'ch_id': c['ch_id'] + 1, 'sub_col_id': 1, 'note_id': 1}]
                    break
            if flag:
                break


def check_multiple_sub_columns(coordinate, indices):
    """判断一列内是否存在多个子列"""
    for i in range(0, len(indices)):
        for j in range(i + 1, len(indices)):
            if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                return 1
    return 0


def compare_y(A, B):
    """比较两个字框的高度，看是否为同高，同高为0，A在B的上侧为-1，A在B的下侧为1"""
    # 定义门限
    threshold = 0.5
    if A['y'] + A['h'] < B['y']:
        return -1
    if B['y'] + B['h'] < A['y']:
        return 1
    if A['y'] < B['y']:
        comm = A['y'] + A['h'] - B['y']
        if float(comm / A['h']) >= threshold or float(comm / B['h']) >= threshold:
            return 0
        else:
            return -1
    else:
        comm = B['y'] + B['h'] - A['y']
        if float(comm / A['h']) >= threshold or float(comm / B['h']) >= threshold:
            return 0
        else:
            return 1


def compare_x(A, B, threshold=0.4):
    """比较两个字框的宽度，看是否为同列，同列为0，A在B的左侧为-1，A在B的右侧为1"""
    if A['x'] + A['w'] < B['x']:
        return -1
    if B['x'] + B['w'] < A['x']:
        return 1
    if A['x'] < B['x']:
        comm = A['x'] + A['w'] - B['x']
        if float(comm / A['w']) >= threshold or float(comm / B['w']) >= threshold:
            return 0
        else:
            return -1
    else:
        comm = B['x'] + B['w'] - A['x']
        if float(comm / A['w']) >= threshold or float(comm / B['w']) >= threshold:
            return 0
        else:
            return 1


def mark_sub_columns(coordinate, char_list, indices):
    """标记列内各字的子列号"""
    char_order = 0
    note_order = 1
    threshold_widest_note_ratio = 0.6
    common_row = [[] for i in range(len(indices))]
    for i in range(0, len(indices)):
        if char_list[indices[i]]['sub_col_id'] != 0:
            continue
        common_row[i] = [indices[i]]
        flag = 0
        # 找到同行的列
        for j in range(i + 1, len(indices)):
            if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                flag = 1
                common_row[i].append(indices[j])
                common_row[j] = common_row[i]
            else:
                break  # 后面更不会有了
        if flag:
            idx_sorted = sorted(range(len(common_row[i])),
                                key=lambda k: coordinate[common_row[i][k]]['x'] + coordinate[common_row[i][k]]['w'],
                                reverse=True)
            order = 1
            for j in range(0, len(idx_sorted)):
                char_list[common_row[i][idx_sorted[j]]]['sub_col_id'] = order
                order = order + 1
                char_list[common_row[i][idx_sorted[j]]]['note_id'] = note_order
                char_list[common_row[i][idx_sorted[j]]]['ch_id'] = char_order
            note_order = note_order + 1
        else:
            flag = 0
            # 判断是不是夹注小字
            if i == 0:
                flag = 1
            else:
                # 前导字是否是大字
                if char_list[indices[i - 1]]['sub_col_id'] == 0:
                    # 判断字框大小
                    if coordinate[indices[i]]['w'] < coordinate[indices[i - 1]]['w'] * threshold_widest_note_ratio:
                        # 字框很窄（不管在左边还是右边）
                        note_order = 1
                        common_row[i] = [indices[i]]
                        char_list[indices[i]]['sub_col_id'] = 1
                        char_list[indices[i]]['note_id'] = note_order
                        char_list[indices[i]]['ch_id'] = char_order
                    else:
                        flag = 1
                else:
                    # 判断跟前字同行的所有字是否列重合
                    last_common_row = common_row[i - 1]
                    # 找到存在多子列的行
                    for j in range(i - 1, -1, -1):
                        if char_list[indices[j]]['sub_col_id'] == 0:
                            break  # 前字为大字，然后呢？
                        if len(common_row[j]) > 1:
                            last_common_row = common_row[j]
                            # print(last_common_row)
                            break
                    if len(last_common_row) == 1:
                        # 如果前字为单列小字，则比较字宽
                        if coordinate[last_common_row[0]]['w'] / threshold_widest_note_ratio \
                                < coordinate[indices[i]]['w']:
                            flag = 1
                        else:
                            # print('I don''t want to see this')
                            char_list[indices[i]]['sub_col_id'] = char_list[indices[i - 1]]['sub_col_id']
                            char_list[indices[i]]['note_id'] = note_order
                            char_list[indices[i]]['ch_id'] = char_order
                            note_order = note_order + 1
                    else:
                        # 前列为多列小字
                        num = 0
                        idx = 0
                        for j in range(0, len(last_common_row)):
                            if compare_x(coordinate[indices[i]], coordinate[last_common_row[j]]) == 0:
                                num = num + 1
                                idx = j
                        if num > 1:
                            flag = 1
                        else:
                            char_list[indices[i]]['sub_col_id'] = char_list[last_common_row[idx]]['sub_col_id']
                            char_list[indices[i]]['note_id'] = note_order
                            char_list[indices[i]]['ch_id'] = char_order
                            note_order = note_order + 1
                            # print(char_list[last_common_row[idx]])
                            # print(char_list[indices[i]])

            # 如果不是
            if flag:
                char_order = char_order + 1
                note_order = 1
                char_list[indices[i]]['ch_id'] = char_order
    return


def mark_sub_columns_knownsmall(coordinate, indices, is_small):
    """给定是否是夹注标记情况下的排序算法"""
    char_order = 0
    note_order = 1

    # 清空标记位
    for i in indices:
        coordinate[i]['sub_col_id'] = 0
        coordinate[i]['note_id'] = 0

    common_row = [[] for i in range(len(indices))]
    for i in range(0, len(indices)):
        if coordinate[indices[i]]['sub_col_id'] != 0:
            continue
        if is_small[i]:
            common_row[i] = [indices[i]]
            flag_multiplesub_column = False
            # 找到同行的列
            for j in range(i + 1, len(indices)):
                if is_small[j]:
                    if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                        flag_multiplesub_column = True
                        common_row[i].append(indices[j])
                        common_row[j] = common_row[i]
                    else:
                        break
                else:
                    break
            if flag_multiplesub_column:
                idx_sorted = sorted(range(len(common_row[i])),
                                    key=lambda k: coordinate[common_row[i][k]]['x'] + coordinate[common_row[i][k]]['w'],
                                    reverse=True)
                order = 1
                for j in range(0, len(idx_sorted)):
                    coordinate[common_row[i][idx_sorted[j]]]['sub_col_id'] = order
                    order = order + 1
                    coordinate[common_row[i][idx_sorted[j]]]['note_id'] = note_order
                    coordinate[common_row[i][idx_sorted[j]]]['ch_id'] = char_order
                note_order = note_order + 1
            else:
                # 一行独字的小字
                # 判断在左边还是在右边
                if i == 0:
                    # 一列的首字
                    # 字框很窄（不管在左边还是右边）
                    note_order = 1
                    coordinate[indices[i]]['sub_col_id'] = 1
                    coordinate[indices[i]]['note_id'] = note_order
                    coordinate[indices[i]]['ch_id'] = char_order
                else:
                    # 前导字是否是大字
                    if not is_small[i - 1]:
                        note_order = 1
                        coordinate[indices[i]]['sub_col_id'] = 1
                        coordinate[indices[i]]['note_id'] = note_order
                        coordinate[indices[i]]['ch_id'] = char_order
                    else:
                        # 判断跟前字同行的所有字是否列重合
                        last_common_row = common_row[i - 1]
                        # 找到存在多子列的行（如果有）
                        for j in range(i - 1, -1, -1):
                            if not is_small[j]:
                                break
                            if len(common_row[j]) > 1:
                                last_common_row = common_row[j]
                                break
                        if len(last_common_row) == 1:
                            # 连续出现的单列小字
                            j = last_common_row[0]
                            if compare_x(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                                # 与前导小字位置一致
                                coordinate[indices[i]]['sub_col_id'] = coordinate[indices[j]]['sub_col_id']
                                coordinate[indices[i]]['note_id'] = note_order
                                coordinate[indices[i]]['ch_id'] = char_order
                                note_order = note_order + 1
                            else:
                                # print('I don''t want to see this')
                                coordinate[indices[i]]['sub_col_id'] = coordinate[indices[j]]['sub_col_id']
                                coordinate[indices[i]]['note_id'] = note_order
                                coordinate[indices[i]]['ch_id'] = char_order
                                note_order = note_order + 1
                        else:
                            # 前列为多列小字
                            for j in range(0, len(last_common_row)):
                                if compare_x(coordinate[indices[i]], coordinate[last_common_row[j]]) == 0:
                                    break
                            coordinate[indices[i]]['sub_col_id'] = coordinate[last_common_row[j]]['sub_col_id']
                            coordinate[indices[i]]['note_id'] = note_order
                            coordinate[indices[i]]['ch_id'] = char_order
                            note_order = note_order + 1

        else:
            # 不是小字
            char_order = char_order + 1
            note_order = 1
            coordinate[indices[i]]['ch_id'] = char_order

    return


def is_contained_in(A, B, threshold=0, ignore_y=False):
    """A是否包含在B当中"""
    threshold = threshold or max(20, B['w'] * 0.25)
    if A['x'] - B['x'] >= -threshold:
        if A['x'] + A['w'] - B['x'] - B['w'] <= threshold:
            if ignore_y or A['y'] - B['y'] >= -threshold:
                if ignore_y or A['y'] + A['h'] - B['y'] - B['h'] <= threshold:
                    return True
    return False


def calc(chars, blocks, columns, sort_after_notecheck=False):
    if sort_after_notecheck:
        """ 输入字框、栏框、列框，输出新的字框数组 """
        # 逐列处理
        for i_b in range(0, len(blocks)):
            for i_c in range(0, len(columns)):
                # 统计列内字框的索引
                char_indices_in_column = []
                flag_changed = False
                for char in chars:
                    if char['column_id'] == i_c + 1 and char['block_id'] == i_b + 1:
                        char_indices_in_column.append(i_c)
                        changed = char.get('is_small')
                        if changed is not None:
                            flag_changed = True
                if flag_changed:
                    # 按高度重新排序
                    idx_sorted = sorted(range(len(char_indices_in_column)),
                                        key=lambda k: chars[char_indices_in_column[k]]['y'])
                    sorted_char_indices = []
                    is_small = []
                    for i in range(0, len(char_indices_in_column)):
                        sorted_char_indices.append(char_indices_in_column[idx_sorted[i]])
                    # 判断列内是否存在夹注小字
                    flag_multiple_sub_columns = False
                    for i in sorted_char_indices:
                        changed = chars[i].get('is_small')
                        if changed is not None:
                            # 校正后是否存在夹注小字
                            if chars[i]['is_small']:
                                flag_multiple_sub_columns = True
                                is_small.append(True)
                            else:
                                # 将错标小字的标记改正
                                chars[i]['sub_col_id'] = 0
                                chars[i]['note_id'] = 0
                                is_small.append(False)
                        else:
                            # 原本是否存在夹注小字
                            if chars[i]['sub_col_id'] != 0:
                                flag_multiple_sub_columns = True
                                is_small.append(True)
                            else:
                                is_small.append(False)
                    # 按高度排序，标记大字
                    if not flag_multiple_sub_columns:
                        order = 1
                        for i in sorted_char_indices:
                            chars[i]['ch_id'] = order
                            chars[i]['column_order'] = order
                            order += 1
                    else:
                        # 标记夹注小字
                        mark_sub_columns_knownsmall(chars, sorted_char_indices, is_small)
                        calc_order(chars, sorted_char_indices)
                else:
                    continue

    else:
        """ 输入字框、栏框、列框，输出新的字框数组{block_id,column_id,ch_id,sub_col_id,note_id,column_order} """
        # 定义新的字框数据结构
        char_list = []
        for i in range(0, len(chars)):
            char_list.append(
                {'block_id': 0, 'column_id': 0, 'ch_id': 0, 'sub_col_id': 0, 'note_id': 0, 'column_order': 0})

        # 按坐标对栏框和列框排序
        blocks = sorted(blocks, key=lambda b: b['y'])
        columns_sorted = []
        for i_b, block in enumerate(blocks):
            block['no'] = i_b + 1
            block['block_id'] = 'b{}'.format(i_b + 1)
            columns_in_block = [column for column in columns
                                if is_contained_in(column, block, max(40, column['w'] / 2), ignore_y=len(blocks) < 2)]
            columns_in_block.sort(key=lambda b: b['x'], reverse=True)
            for i_c, column in enumerate(columns_in_block):
                column['no'] = i_c + 1
                column['block_no'] = i_b + 1
                column['column_id'] = block['block_id'] + 'c{}'.format(i_c + 1)
            columns_sorted += columns_in_block
        columns = columns_sorted

        # 标记栏框和列框
        for i, c in enumerate(chars):
            for column in columns:
                if is_contained_in(c, column):
                    char_list[i]['block_id'] = column['block_no']
                    char_list[i]['column_id'] = column['no']
                    c['block_no'] = column['block_no']
                    c['line_no'] = column['no']
            if not c.get('block_no') or not c.get('line_no'):
                pass  # print(c)

        # 逐列处理
        for column in columns:
            # 统计列内字框的索引
            if not column.get('block_no'):
                print(column)
            char_indices_in_column = [i for i, c in enumerate(chars) if c.get('block_no') == column['block_no']
                                      and c.get('line_no') == column['no']]
            # 按高度重新排序
            sorted_char_indices = sorted(char_indices_in_column, key=lambda i: chars[i]['y'])

            # 判断是否存在夹注小字
            flag_multiple_sub_columns = check_multiple_sub_columns(chars, sorted_char_indices)
            # 按高度排序，标记大字
            if flag_multiple_sub_columns == 0:
                order = 1
                for i in sorted_char_indices:
                    char_list[i]['ch_id'] = order
                    char_list[i]['column_order'] = order
                    order += 1
            else:
                # 标记夹注小字
                mark_sub_columns(chars, char_list, sorted_char_indices)
                calc_order(char_list, sorted_char_indices)
    # 输出数据
    return char_list


def test():
    # 文件路径
    filename = __file__[:-5] + "../../tests/data/JX/JX_165_7_12"
    # 加载字框数据
    with open(filename + ".json", 'r', encoding='UTF-8') as load_f:
        data_dict = json.load(load_f)
        coordinate_char_list = data_dict['chars']
        # 加载栏框和列框数据
        # with open(filename + "_column" + ".json", 'r') as load_f:
        coordinate_block_list = data_dict['blocks']
        coordinate_column_list = data_dict['columns']

    result = calc(coordinate_char_list, coordinate_block_list, coordinate_column_list)
    print(json.dumps(result))


if __name__ == '__main__':
    import json

    test()
