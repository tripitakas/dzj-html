import sys
import os
sys.path.append(os.path.dirname(__file__))

from check_mulsubcol import check_multiple_subcolumns
from mark_mulsubcol import mark_subcolumns
from mark_mulsubcol import mark_subcolumns_knownsmall
from use_noteid import calc_order


# A 是否包含在B当中
def is_contained_in(A, B, threshold=0, ignore_y=False):
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
                    flag_multiple_subcolumns = False
                    for i in sorted_char_indices:
                        changed = chars[i].get('is_small')
                        if changed is not None:
                            # 校正后是否存在夹注小字
                            if chars[i]['is_small']:
                                flag_multiple_subcolumns = True
                                is_small.append(True)
                            else:
                                # 将错标小字的标记改正
                                chars[i]['subcolumn_id'] = 0
                                chars[i]['note_id'] = 0
                                is_small.append(False)
                        else:
                            # 原本是否存在夹注小字
                            if chars[i]['subcolumn_id'] != 0:
                                flag_multiple_subcolumns = True
                                is_small.append(True)
                            else:
                                is_small.append(False)
                    # 按高度排序，标记大字
                    if not flag_multiple_subcolumns:
                        order = 1
                        for i in sorted_char_indices:
                            chars[i]['ch_id'] = order
                            chars[i]['column_order'] = order
                            order += 1
                    else:
                        # 标记夹注小字
                        mark_subcolumns_knownsmall(chars, sorted_char_indices, is_small)
                        calc_order(chars, sorted_char_indices)
                else:
                    continue

    else:
        """ 输入字框、栏框、列框，输出新的字框数组{block_id,column_id,ch_id,subcolumn_id,note_id,column_order} """
        # 定义新的字框数据结构
        char_list = []
        for i in range(0, len(chars)):
            char_list.append(
                {'block_id': 0, 'column_id': 0, 'ch_id': 0, 'subcolumn_id': 0, 'note_id': 0, 'column_order': 0})

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
            flag_multiple_subcolumns = check_multiple_subcolumns(chars, sorted_char_indices)
            # 按高度排序，标记大字
            if flag_multiple_subcolumns == 0:
                order = 1
                for i in sorted_char_indices:
                    char_list[i]['ch_id'] = order
                    char_list[i]['column_order'] = order
                    order += 1
            else:
                # 标记夹注小字
                mark_subcolumns(chars, char_list, sorted_char_indices)
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
