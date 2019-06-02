from check_mulsubcol import compare_y


# 找到多列
def check_multiple_subcolumns(coordinate, indices):
    for i in range(0, len(indices)):
        for j in range(i + 1, len(indices)):
            if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                return 1
    return 0


# 比较两个字框的宽度，看是否为同列
# 同列为0，A在B的左侧为-1，A在B的右侧为1


def compare_x(A, B, threshold=0.4):
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


# 标记列内各字的子列号


def mark_subcolumns(coordinate, char_list, indices):
    char_order = 0
    note_order = 1
    threshold_widest_note_ratio = 0.6
    common_row = [[] for i in range(len(indices))]
    for i in range(0, len(indices)):
        if char_list[indices[i]]['subcolumn_id'] != 0:
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
                char_list[common_row[i][idx_sorted[j]]]['subcolumn_id'] = order
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
                if char_list[indices[i - 1]]['subcolumn_id'] == 0:
                    # 判断字框大小
                    if coordinate[indices[i]]['w'] < coordinate[indices[i - 1]]['w'] * threshold_widest_note_ratio:
                        # 字框很窄（不管在左边还是右边）
                        note_order = 1
                        common_row[i] = [indices[i]]
                        char_list[indices[i]]['subcolumn_id'] = 1
                        char_list[indices[i]]['note_id'] = note_order
                        char_list[indices[i]]['ch_id'] = char_order
                    else:
                        flag = 1
                else:
                    # 判断跟前字同行的所有字是否列重合
                    last_common_row = common_row[i - 1]
                    # 找到存在多子列的行
                    for j in range(i - 1, -1, -1):
                        if char_list[indices[j]]['subcolumn_id'] == 0:
                            break  # 前字为大字，然后呢？
                        if len(common_row[j]) > 1:
                            last_common_row = common_row[j]
                            # print(last_common_row)
                            break
                    if len(last_common_row) == 1:
                        # 如果前字为单列小字，则比较字宽
                        if coordinate[indices[i]]['w'] > coordinate[last_common_row[0]][
                            'w'] / threshold_widest_note_ratio:
                            flag = 1
                        else:
                            # print('I don''t want to see this')
                            char_list[indices[i]]['subcolumn_id'] = char_list[indices[i - 1]]['subcolumn_id']
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
                            char_list[indices[i]]['subcolumn_id'] = char_list[last_common_row[idx]]['subcolumn_id']
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


# 给定是否是夹注标记情况下的排序算法


def mark_subcolumns_knownsmall(coordinate, indices, is_small):
    char_order = 0
    note_order = 1

    # 清空标记位
    for i in indices:
        coordinate[i]['subcolumn_id'] = 0
        coordinate[i]['note_id'] = 0

    common_row = [[] for i in range(len(indices))]
    for i in range(0, len(indices)):
        if coordinate[indices[i]]['subcolumn_id'] != 0:
            continue
        if is_small[i]:
            common_row[i] = [indices[i]]
            flag_multiplesubcolumn = False
            # 找到同行的列
            for j in range(i + 1, len(indices)):
                if is_small[j]:
                    if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                        flag_multiplesubcolumn = True
                        common_row[i].append(indices[j])
                        common_row[j] = common_row[i]
                    else:
                        break
                else:
                    break
            if flag_multiplesubcolumn:
                idx_sorted = sorted(range(len(common_row[i])),
                                    key=lambda k: coordinate[common_row[i][k]]['x'] + coordinate[common_row[i][k]]['w'],
                                    reverse=True)
                order = 1
                for j in range(0, len(idx_sorted)):
                    coordinate[common_row[i][idx_sorted[j]]]['subcolumn_id'] = order
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
                    coordinate[indices[i]]['subcolumn_id'] = 1
                    coordinate[indices[i]]['note_id'] = note_order
                    coordinate[indices[i]]['ch_id'] = char_order
                else:
                    # 前导字是否是大字
                    if not is_small[i - 1]:
                        note_order = 1
                        coordinate[indices[i]]['subcolumn_id'] = 1
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
                                coordinate[indices[i]]['subcolumn_id'] = coordinate[indices[j]]['subcolumn_id']
                                coordinate[indices[i]]['note_id'] = note_order
                                coordinate[indices[i]]['ch_id'] = char_order
                                note_order = note_order + 1
                            else:
                                # print('I don''t want to see this')
                                coordinate[indices[i]]['subcolumn_id'] = coordinate[indices[j]]['subcolumn_id']
                                coordinate[indices[i]]['note_id'] = note_order
                                coordinate[indices[i]]['ch_id'] = char_order
                                note_order = note_order + 1
                        else:
                            # 前列为多列小字
                            for j in range(0, len(last_common_row)):
                                if compare_x(coordinate[indices[i]], coordinate[last_common_row[j]]) == 0:
                                    break
                            coordinate[indices[i]]['subcolumn_id'] = coordinate[last_common_row[j]]['subcolumn_id']
                            coordinate[indices[i]]['note_id'] = note_order
                            coordinate[indices[i]]['ch_id'] = char_order
                            note_order = note_order + 1

        else:
            # 不是小字
            char_order = char_order + 1
            note_order = 1
            coordinate[indices[i]]['ch_id'] = char_order

    return
