import sys
import os
sys.path.append(os.path.dirname(__file__))

# --------------------20190113上午修改--------------------------------------------------------------------#
# A 是否包含在B当中


def is_contained_in(A, B):
    threshold = 0
    if (A['x'] + A['w'] - B['x'] <= threshold) or (A['x'] - B['x'] - B['w'] >= threshold) \
            or (A['y'] - B['y'] - B['h'] >= threshold) or (A['y'] + A['h'] - B['y'] <= threshold):
        return False
    return True


# --------------------20190113上午修改--------------------------------------------------------------------#
# 计算各字框之间的链接关系


def calc_connections(coordinate, indices, connection):
    # 字框重合比例超过ratio，认为有效
    ratio = 0.3
    # 字框高度差比例超过ratio_h，认为字框在另一字框下方
    ratio_h = 0.3
    # --------------------20190112下午添加--------------------------------------------------------------------#
    # 字框重合比例超过ratio，认为是一一链接
    ratio_one_one = 0.8
    # --------------------20190112下午添加--------------------------------------------------------------------#
    # 逐字框处理
    for i in range(0, len(indices)):
        a = coordinate[indices[i]]
        # 定义距离: {'index':,'y_diff':,'x_overlap_left':,'x_overlap_left'}
        dist = []
        # 计算距离，并确定下方字框
        for j in range(0, len(indices)):
            if j == i:
                continue
            # --------------------20190112下午添加--------------------------------------------------------------------#
            # 排除已确定一一链接的字框
            if connection[indices[j]]['Mono_Uplink_Flag']:
                continue
            # --------------------20190112下午添加--------------------------------------------------------------------#
            b = coordinate[indices[j]]
            # 仅考虑比a低的字框
            if b['y'] < a['y']:
                continue
            # 仅考虑与a的x坐标有重合的字框
            if (b['x'] > a['x'] + a['w']) or (b['x'] + b['w'] < a['x']):
                continue
            # 计算纵向距离
            y_diff = b['y'] - a['y'] - a['h']
            # 计算左重合点
            x_overlap_left = max(a['x'], b['x'])
            # 计算右重合点
            x_overlap_right = min(a['x'] + a['w'], b['x'] + b['w'])
            # 计算重合长度
            w_overlap = x_overlap_right - x_overlap_left
            # 仅考虑重合比例超过门限的字框
            if (w_overlap > ratio * a['w']) or (w_overlap > ratio * b['w']):
                dist.append({'index': indices[j],
                             'y_diff': y_diff,
                             'x_overlap_left': x_overlap_left,
                             'x_overlap_right': x_overlap_right})
        # 确定相邻下方字框
        down_neighbor = []
        for j in range(0, len(dist)):
            candidate_flag = True
            for k in range(0, len(dist)):
                if k == j:
                    continue
                # overlap是否重合
                if (dist[j]['x_overlap_left'] > dist[k]['x_overlap_right']) \
                        or (dist[k]['x_overlap_left'] > dist[j]['x_overlap_right']):
                    pass
                else:
                    # 是否在j对应字框上方
                    if dist[j]['y_diff'] > dist[k]['y_diff'] + ratio_h * coordinate[dist[k]['index']]['h']:
                        candidate_flag = False
            if candidate_flag:
                down_neighbor.append(dist[j]['index'])
        # --------------------20190112下午添加--------------------------------------------------------------------#
        # 判断是不是一一链接
        Mono_Uplink_Flag = False
        for j in down_neighbor:
            b = coordinate[j]
            # 计算左重合点
            x_overlap_left = max(a['x'], b['x'])
            # 计算右重合点
            x_overlap_right = min(a['x'] + a['w'], b['x'] + b['w'])
            # 计算重合长度
            w_overlap = x_overlap_right - x_overlap_left
            # 重合比例超过门限
            if (w_overlap > ratio_one_one * a['w']) and (w_overlap > ratio_one_one * b['w']):
                connection[j]['Mono_Uplink_Flag'] = True
                connection[indices[i]]['Down'].append(j)
                connection[j]['Up'].append(indices[i])
                Mono_Uplink_Flag = True
                break
        if Mono_Uplink_Flag:
            continue
        # --------------------20190112下午添加--------------------------------------------------------------------#
        # 更新链接关系
        for j in down_neighbor:
            connection[indices[i]]['Down'].append(j)
            connection[j]['Up'].append(indices[i])
    return


# --------------------20190112下午添加--------------------------------------------------------------------#


# 删除无效链接关系
def delete_connections(coordinate, indices, connection, case=0):
    # 空格超过threthold，则认为不在同一列
    threthold = 5
    for i in indices:
        a_c = connection[i]
        # 删除字歪斜导致的飞线情况
        if len(a_c['Down']) == 0:
            continue
        if case == 1 or case == 0:
            # a 下连多，b上连多
            if len(a_c['Down']) >= 2:
                tmp_down = a_c['Down'].copy()
                for j in tmp_down:
                    b_c = connection[j]
                    if len(b_c['Up']) >= 2 and len(a_c['Down']) >= 2:
                        # --------------------20190113上午修改--------------------------------------------------------------------#
                        # 计算各链接之间的距离，将距离最大的链接删除
                        a = coordinate[i]
                        dist_a_down = []
                        for i_a in a_c['Down']:
                            tmp_dist_h = -(a['y'] + a['h']) + coordinate[i_a]['y']
                            # 计算左重合点
                            x_overlap_left = max(a['x'], coordinate[i_a]['x'])
                            # 计算右重合点
                            x_overlap_right = min(a['x'] + a['w'], coordinate[i_a]['x'] + coordinate[i_a]['w'])
                            # 计算重合长度
                            w_overlap = x_overlap_right - x_overlap_left
                            dist_a_down.append(tmp_dist_h - w_overlap)
                        b = coordinate[j]
                        dist_b_up = []
                        for i_a in b_c['Up']:
                            tmp_dist_h = b['y'] - (coordinate[i_a]['y'] + coordinate[i_a]['h'])
                            # 计算左重合点
                            x_overlap_left = max(b['x'], coordinate[i_a]['x'])
                            # 计算右重合点
                            x_overlap_right = min(b['x'] + b['w'], coordinate[i_a]['x'] + coordinate[i_a]['w'])
                            # 计算重合长度
                            w_overlap = x_overlap_right - x_overlap_left
                            dist_b_up.append(tmp_dist_h - w_overlap)
                        if max(dist_a_down) == max(dist_b_up):
                            a_c['Down'].remove(j)
                            b_c['Up'].remove(i)
                        elif max(dist_a_down) > max(dist_b_up):
                            arg_max = max(range(len(dist_a_down)), key=lambda p: dist_a_down[p])
                            connection[a_c['Down'][arg_max]]['Up'].remove(i)
                            a_c['Down'].remove(a_c['Down'][arg_max])
                        else:
                            arg_max = max(range(len(dist_b_up)), key=lambda p: dist_b_up[p])
                            connection[b_c['Up'][arg_max]]['Down'].remove(j)
                            b_c['Up'].remove(b_c['Up'][arg_max])
                            # --------------------20190113上午修改--------------------------------------------------------------------#
        if case == 2 or case == 0:
            tmp_down = a_c['Down'].copy()
            for j in tmp_down:
                b_c = connection[j]
                if len(b_c['Up']) >= 2:
                    a = coordinate[i]
                    tmp_up = b_c['Up'].copy()
                    for k in tmp_up:
                        if k != i:
                            c = coordinate[k]
                            if c['y'] > a['y'] + a['h'] * threthold:
                                a_c['Down'].remove(j)
                                b_c['Up'].remove(i)
                                break
                                # --------------------20190113上午添加--------------------------------------------------------------------#
                                # 删除N型链接关系
                                # 删除众型链接关系
                                # 删除倒众型链接关系
                                # --------------------20190113上午添加--------------------------------------------------------------------#

    return


# --------------------20190112下午添加--------------------------------------------------------------------#


# 对同列的字框标上列序号
def mark_column_id(char_list, connection, coordinate_char_list, idx, marker, direction):
    A = char_list[idx]
    a_c = connection[idx]
    if A['column_id'] != 0:
        return
    A['column_id'] = marker
    # 向下搜索
    if direction == 0 or direction == 1:
        if len(a_c['Down']) == 0:
            if direction == 1:
                return
        elif len(a_c['Down']) == 1:
            next_idx = a_c['Down'][0]
            mark_column_id(char_list, connection, coordinate_char_list, next_idx, marker, 1)
            B = char_list[next_idx]
            b_c = connection[next_idx]
            if len(b_c['Up']) >= 2:
                idx_sorted = sorted(range(len(b_c['Up'])),
                                    key=lambda k: coordinate_char_list[b_c['Up'][k]]['x']
                                                  + coordinate_char_list[b_c['Up'][k]]['w'],
                                    reverse=True)
                for i in range(0, len(idx_sorted)):
                    subidx = b_c['Up'][idx_sorted[i]]
                    mark_subcolumn_id(char_list, connection, subidx, i + 1, -1)
                    if subidx != idx:
                        mark_column_id(char_list, connection, coordinate_char_list, subidx, marker, -1)
        elif len(a_c['Down']) >= 2:
            idx_sorted = sorted(range(len(a_c['Down'])),
                                key=lambda k: coordinate_char_list[a_c['Down'][k]]['x']
                                              + coordinate_char_list[a_c['Down'][k]]['w'],
                                reverse=True)
            for i in range(0, len(idx_sorted)):
                subidx = a_c['Down'][idx_sorted[i]]
                mark_subcolumn_id(char_list, connection, subidx, i + 1, 1)
                mark_column_id(char_list, connection, coordinate_char_list, subidx, marker, 1)
        else:
            # 异常情况
            return
    # 向上搜索
    if direction == 0 or direction == -1:
        if len(a_c['Up']) == 0:
            return
        elif len(a_c['Up']) == 1:
            next_idx = a_c['Up'][0]
            mark_column_id(char_list, connection, coordinate_char_list, next_idx, marker, -1)
            B = char_list[next_idx]
            b_c = connection[next_idx]
            if len(b_c['Down']) >= 2:
                idx_sorted = sorted(range(len(b_c['Down'])),
                                    key=lambda k: coordinate_char_list[b_c['Down'][k]]['x']
                                                  + coordinate_char_list[b_c['Down'][k]]['w'],
                                    reverse=True)
                for i in range(0, len(idx_sorted)):
                    subidx = b_c['Down'][idx_sorted[i]]
                    mark_subcolumn_id(char_list, connection, subidx, i + 1, 1)
                    if subidx != idx:
                        mark_column_id(char_list, connection, coordinate_char_list, subidx, marker, 1)
        elif len(a_c['Up']) >= 2:
            idx_sorted = sorted(range(len(a_c['Up'])),
                                key=lambda k: coordinate_char_list[a_c['Up'][k]]['x']
                                              + coordinate_char_list[a_c['Up'][k]]['w'],
                                reverse=True)
            for i in range(0, len(idx_sorted)):
                subidx = a_c['Up'][idx_sorted[i]]
                mark_subcolumn_id(char_list, connection, subidx, i + 1, -1)
                mark_column_id(char_list, connection, coordinate_char_list, subidx, marker, -1)

        else:
            # 异常情况
            return


# ----------------------------------------------------------------------------------------#


# 标记夹注子列的序号
def mark_subcolumn_id(char_list, connection, idx, marker, direction):
    A = char_list[idx]
    a_c = connection[idx]
    if A['subcolumn_id'] != 0:
        return
    A['subcolumn_id'] = marker
    # 向下搜索
    if direction == 1:
        if len(a_c['Down']) == 0:
            return
        elif len(a_c['Down']) == 1:
            next_idx = a_c['Down'][0]
            b_c = connection[next_idx]
            if len(b_c['Up']) == 1:
                mark_subcolumn_id(char_list, connection, next_idx, marker, 1)
            elif len(b_c['Up']) >= 2:
                return
        else:
            return
    # 向上搜索
    if direction == -1:
        if len(a_c['Up']) == 0:
            return
        elif len(a_c['Up']) == 1:
            next_idx = a_c['Up'][0]
            b_c = connection[next_idx]
            if len(b_c['Down']) == 1:
                mark_subcolumn_id(char_list, connection, next_idx, marker, -1)
            elif len(b_c['Down']) >= 2:
                return
        else:
            return


# ----------------------------------------------------------------------------------------#


# 标记列内ch_id
def mark_ch_id(char_list, connection, idx, marker):
    A = char_list[idx]
    a_c = connection[idx]
    if A['ch_id'] != 0:
        return
    else:
        A['ch_id'] = marker
        if len(a_c['Down']) == 0:
            return
        elif len(a_c['Down']) == 1:
            next_idx = a_c['Down'][0]
            mark_ch_id(char_list, connection, next_idx, marker + 1)
        else:
            for j in a_c['Down']:
                #                mark_ch_id(char_list, j, marker)
                char_list[j]['ch_id'] = marker
                mark_note_id(char_list, connection, j, 1)
    return


# ----------------------------------------------------------------------------------------


# 标记subcolumn内的note_id
def mark_note_id(char_list, connection, idx, marker):
    A = char_list[idx]
    a_c = connection[idx]
    # print(idx)
    # print(connection[idx])
    A['note_id'] = marker
    if len(a_c['Down']) == 0:
        return
    elif len(a_c['Down']) == 1:
        next_idx = a_c['Down'][0]
        B = char_list[next_idx]
        b_c = connection[next_idx]
        if len(b_c['Up']) == 1:
            B['ch_id'] = A['ch_id']
            mark_note_id(char_list, connection, next_idx, marker + 1)
        else:
            if B['ch_id'] == 0:
                mark_ch_id(char_list, connection, next_idx, A['ch_id'] + 1)
    else:
        # 夹注出现夹注，异常情况
        return
    return


# ----------------------------------------------------------------------------------------#
# 根据列号、子列号等，计算列内序号
def calc_order(char_list, indices):
    candidates = [{'ch_id': 0, 'subcolumn_id': 1, 'note_id': 1},
                  {'ch_id': 1, 'subcolumn_id': 0, 'note_id': 0}]
    for order in range(0, len(indices)):
        flag = 0
        for cnddt in candidates:
            for i in indices:
                if char_list[i]['ch_id'] == cnddt['ch_id'] and char_list[i]['subcolumn_id'] == cnddt['subcolumn_id'] and \
                                char_list[i]['note_id'] == cnddt['note_id']:
                    flag = 1
                    char_list[i]['column_order'] = order + 1
                    if cnddt['subcolumn_id'] != 0:
                        # 这个字是小字
                        candidates = [{'ch_id': char_list[i]['ch_id'], 'subcolumn_id': char_list[i]['subcolumn_id'],
                                       'note_id': char_list[i]['note_id'] + 1},
                                      {'ch_id': char_list[i]['ch_id'], 'subcolumn_id': char_list[i]['subcolumn_id'] + 1,
                                       'note_id': 1},
                                      {'ch_id': char_list[i]['ch_id'] + 1, 'subcolumn_id': 0, 'note_id': 0},
                                      {'ch_id': char_list[i]['ch_id'] + 1, 'subcolumn_id': 1, 'note_id': 1}]
                    else:
                        candidates = [{'ch_id': char_list[i]['ch_id'], 'subcolumn_id': 1, 'note_id': 1},
                                      {'ch_id': char_list[i]['ch_id'] + 1, 'subcolumn_id': 0, 'note_id': 0},
                                      {'ch_id': char_list[i]['ch_id'] + 1, 'subcolumn_id': 1, 'note_id': 1}]
                    break
            if flag:
                break


# ----------------------------------------------------------------------------------------#
# 显示字框
def show(char_list, coordinate_char_list, indices, ax, filename):
    for i in indices:
        xleft = coordinate_char_list[i]['x']
        xright = xleft + coordinate_char_list[i]['w']
        yup = coordinate_char_list[i]['y']
        ydown = yup + coordinate_char_list[i]['h']
        A = char_list[i]
        if A['subcolumn_id'] == 0:
            # plt.plot([xleft,xright],[yup,yup],'r-')
            # plt.plot([xleft, xright], [ydown, ydown], 'r-')
            # plt.plot([xleft, xleft], [yup, ydown], 'r-')
            # plt.plot([xright, xright], [yup, ydown], 'r-')
            rect = plt.Rectangle((xleft, yup), coordinate_char_list[i]['w'], coordinate_char_list[i]['h'], color='r',
                                 alpha=0.1)
            ax.add_patch(rect)
        else:
            radius = min([coordinate_char_list[i]['h'], coordinate_char_list[i]['w']]) / 2
            circ = plt.Circle(((xleft + xright) / 2, (yup + ydown) / 2), radius, color='g', alpha=0.5)  # 圆心，半径，颜色，α
            ax.add_patch(circ)
        #        plt.text(xleft,-ydown,str(i)+','+str(A['Up'])+','+str(A['Down']))
        #        plt.text(xleft,-ydown,str(A['column_id'])+'-'+str(A['ch_id'])+'-'+str(A['subcolumn_id'])+'-'+str(A['note_id']))
        #        plt.text(xleft, ydown,str(A['column_order']))
    plt.savefig(filename, dpi=300)

    #    plt.show()
    # 显示字框
    def show(char_list, coordinate_char_list, indices, ax, filename):
        for i in indices:
            xleft = coordinate_char_list[i]['x']
            xright = xleft + coordinate_char_list[i]['w']
            yup = coordinate_char_list[i]['y']
            ydown = yup + coordinate_char_list[i]['h']
            A = char_list[i]
            if A['subcolumn_id'] == 0:
                # plt.plot([xleft,xright],[yup,yup],'r-')
                # plt.plot([xleft, xright], [ydown, ydown], 'r-')
                # plt.plot([xleft, xleft], [yup, ydown], 'r-')
                # plt.plot([xright, xright], [yup, ydown], 'r-')
                rect = plt.Rectangle((xleft, yup), coordinate_char_list[i]['w'], coordinate_char_list[i]['h'],
                                     color='r', alpha=0.1)
                ax.add_patch(rect)
            else:
                radius = min([coordinate_char_list[i]['h'], coordinate_char_list[i]['w']]) / 2
                circ = plt.Circle(((xleft + xright) / 2, (yup + ydown) / 2), radius, color='g', alpha=0.5)  # 圆心，半径，颜色，α
                ax.add_patch(circ)
        # plt.text(xleft,-ydown,str(i)+','+str(A['Up'])+','+str(A['Down']))
        #        plt.text(xleft,-ydown,str(A['column_id'])+'-'+str(A['ch_id'])+'-'+str(A['subcolumn_id'])+'-'+str(A['note_id']))
        #        plt.text(xleft, ydown,str(A['column_order']))
        plt.savefig(filename, dpi=300)

    #    plt.show()
    return


# ----------------------------------------------------------------------------------------#

# 显示字框
def show2(char_list, coordinate_char_list, indices, ax, filename):
    for i in indices:
        xleft = coordinate_char_list[i]['x']
        xright = xleft + coordinate_char_list[i]['w']
        yup = coordinate_char_list[i]['y']
        ydown = yup + coordinate_char_list[i]['h']
        A = char_list[i]
        if A['subcolumn_id'] == 0:
            plt.plot([xleft, xright], [-yup, -yup], 'r-')
            plt.plot([xleft, xright], [-ydown, -ydown], 'r-')
            plt.plot([xleft, xleft], [-yup, -ydown], 'r-')
            plt.plot([xright, xright], [-yup, -ydown], 'r-')
            # rect = plt.Rectangle((xleft, yup), coordinate_char_list[i]['w'], coordinate_char_list[i]['h'], color='r', alpha=0.1)
            # ax.add_patch(rect)
        else:
            radius = min([coordinate_char_list[i]['h'], coordinate_char_list[i]['w']]) / 2
            circ = plt.Circle(((xleft + xright) / 2, (-yup - ydown) / 2), radius, color='g', alpha=0.5)  # 圆心，半径，颜色，α
            ax.add_patch(circ)
        # plt.text(xleft,-ydown,str(A['column_id'])+'-'+str(A['ch_id'])+'-'+str(A['subcolumn_id'])+'-'+str(A['note_id']))
        # plt.text(xright, -ydown, str(i))
        plt.text(xleft, -ydown, str(A['column_order']))
        # plt.text(xleft, -ydown, str(A['column_id'])+'-'+str(A['column_order']))


#    plt.savefig(filename, dpi = 300)
#    plt.show()

# ----------------------------------------------------------------------------------------#



# 显示连线
def show_downconnection(coordinate, connection, indices):
    for i in range(0, len(indices)):
        idx = indices[i]
        a = coordinate[idx]
        a_c = connection[idx]
        if len(a_c['Down']) == 0:
            continue
        a_x = a['x'] + a['w'] * 1 / 2
        a_y = a['y'] + a['h'] * 1 / 2
        for j in a_c['Down']:
            b = coordinate[j]
            b_x = b['x'] + b['w'] * 1 / 2
            b_y = b['y'] + b['h'] * 1 / 2
            plt.plot([a_x, b_x], [-a_y, -b_y], 'g-')
            # plt.text(a['x'], -(a['y'] + a['h']), str(int(a_c['Mono_Uplink_Flag'])))
    return


# ----------------------------------------------------------------------------------------#



# 显示连线
def show_connection(char_list, coordinate_char_list, indices):
    for order in range(1, len(indices)):
        for i in indices:
            if char_list[i]['column_order'] == order:
                A = coordinate_char_list[i]
            if char_list[i]['column_order'] == order + 1:
                B = coordinate_char_list[i]
        Ax = A['x'] + A['w'] * 3 / 4
        Ay = A['y'] + A['h'] * 3 / 4
        Bx = B['x'] + B['w'] * 3 / 4
        By = B['y'] + B['h'] * 1 / 4
        if Ay < By:
            plt.plot([Ax, Bx], [Ay, By], 'g-')
            # plt.arrow(Ax,Ay, Bx-Ax, By-Ay, color='g', linestyle='-')
        else:
            plt.plot([Ax, Bx], [Ay, By], 'r-')
    return


connections = []

# ----------------------------------------------------------------------------------------#
# 主计算函数，在Web服务和__main__中使用


def calc(chars, blocks, columns=None):
    # 定义新的字框数据结构
    char_list = []
    del connections[:]
    for i in range(0, len(chars)):
        char_list.append(
            {'block_id': 0, 'column_id': 0, 'ch_id': 0, 'subcolumn_id': 0, 'note_id': 0, 'column_order': 0})
        # --------------------20190112下午修改--------------------------------------------------------------------#
        connections.append({'Up': [], 'Down': [], 'Mono_Uplink_Flag': False})
        # --------------------20190112下午修改--------------------------------------------------------------------#
    # 标记栏框
    for i in range(0, len(chars)):
        for i_b in range(0, len(blocks)):
            if is_contained_in(chars[i], blocks[i_b]):
                char_list[i]['block_id'] = i_b + 1
                # -------------------------
                # 检查是否存在没有标记栏序的字框
                # 云贵师兄： 能否完善该部分？
                # -------------------------
                ##########################################################################
    # 逐栏处理
    for i_b in range(0, len(blocks)):
        # 统计列内字框的索引
        char_indices_in_block = []
        for i in range(0, len(chars)):
            if char_list[i]['block_id'] == i_b + 1:
                char_indices_in_block.append(i)
        calc_connections(chars, char_indices_in_block, connections)
        # --------------------20190113上午修改--------------------------------------------------------------------#
        # 删除无效链接关系
        delete_connections(chars, char_indices_in_block, connections, 1)
        delete_connections(chars, char_indices_in_block, connections, 2)
        # --------------------20190113上午修改--------------------------------------------------------------------#
        # print(connections)
        # print(connections[2])
        # print(connections[3])
        # print(connections[8])
        # 对字框从右到左排序
        idx_sorted = sorted(range(len(char_indices_in_block)),
                            key=lambda k: chars[char_indices_in_block[k]]['x'],
                            reverse=True)
        # 标记列号
        column_marker = 1
        for i in idx_sorted:
            idx = char_indices_in_block[i]
            if char_list[idx]['column_id'] == 0:
                mark_column_id(char_list, connections, chars, idx, column_marker, 0)
                column_marker = column_marker + 1
            else:
                continue
        # -------------------------
        # 检查是否存在没有标记列号的字框
        # 云贵师兄： 能否完善该部分？
        # -------------------------
        # 对列内字号、夹注号进行标注
        for i in char_indices_in_block:
            A = char_list[i]
            a_c = connections[i]
            if A['block_id'] == 0:
                # 异常情况
                continue
            else:
                # 列内首字开始编号
                if len(a_c['Up']) == 0:
                    if A['subcolumn_id'] == 0:
                        mark_ch_id(char_list, connections, i, 1)
                    else:
                        mark_note_id(char_list, connections, i, 1)
                else:
                    continue
        # 根据列号，子列号等，进行列内排序
        for i in range(1, column_marker):
            char_indices_in_column = []
            for k in char_indices_in_block:
                if char_list[k]['column_id'] == i:
                    char_indices_in_column.append(k)
            calc_order(char_list, char_indices_in_column)
            # -------------------------
            # 检查是否存在没有标记列内序号的字框
            # 云贵师兄： 能否完善该部分？
            # -------------------------
    if columns:
        merge_columns(char_list, columns, chars)
    return char_list


def find_nearest_box(box, boxes):
    min_d = 1e7
    ret = -1
    for i, b in enumerate(boxes):
        if box['y2'] > b['y'] and box['y'] < b['y'] + b['h']:
            dx = abs((box['x'] + box['x2']) / 2 - b['x'] - b['w'] / 2)
            if min_d > dx:
                min_d = dx
                ret = i
    return ret


def has_note_in_column(chars_in):
    return [c for c in chars_in if c['subcolumn_id']]


def merge_columns(new_chars, columns, chars_ocr):
    column_ids = ['b%dc%02d' % (c['block_id'], c['column_id']) for i, c in enumerate(new_chars)]
    new_columns = sorted(list(set(column_ids)))
    # 先比较列框个数：新算法得到的列框个数 > 列框校对后列框个数
    if len(new_columns) > len(columns):
        # 合并新算法得到的列框
        column_boxes = {}
        for i, (column_id, c) in enumerate(zip(column_ids, chars_ocr)):
            if column_id not in column_boxes:
                column_boxes[column_id] = dict(x=c['x'], y=c['y'], x2=c['x'] + c['w'], y2=c['y'] + c['h'])
            else:
                column_boxes[column_id]['x'] = min(column_boxes[column_id]['x'], c['x'])
                column_boxes[column_id]['y'] = min(column_boxes[column_id]['y'], c['y'])
                column_boxes[column_id]['x2'] = max(column_boxes[column_id]['x2'], c['x'] + c['w'])
                column_boxes[column_id]['y2'] = max(column_boxes[column_id]['y2'], c['y'] + c['h'])

        # 判断新算法得到的各列所在的列框校对后的列框索引
        index_column = [find_nearest_box(column_boxes[c], columns) for c in new_columns]

        # 判断新算法得到的列数据是否存在下列情况：相邻的两个仅包含大字的列有相同的列框索引
        block_no, column_no, chars_prev = None, 0, []
        for i, idx in enumerate(index_column):
            chars_cur = [c for ci, c in enumerate(new_chars) if column_ids[ci] == new_columns[i]]
            if block_no != chars_cur[0]['block_id']:
                block_no = chars_cur[0]['block_id']
                column_no = 0
                chars_prev = []
            column_no += 1
            if chars_prev and idx >= 0 and idx == index_column[i - 1] \
                    and not has_note_in_column(chars_cur) \
                    and not has_note_in_column(chars_prev):
                # print('%s merge columns: %s %s' % (name, new_columns[i], new_columns[i - 1]))
                column_no -= 1
                for ci, c in enumerate(chars_cur):
                    c['column_order'] = len(chars_prev) + ci + 1
                chars_cur = chars_prev + chars_cur
            for ci, c in enumerate(chars_cur):
                c['column_id'] = column_no
            chars_prev = chars_cur


def test():
    # 文件路径
    # 师兄只需要看这几个页面："JX_245_2_155", "JX_245_3_67", "JX_245_3_87", "JX_254_5_218", "JX_260_1_206", "JX_260_1_241", "JX_260_1_256"
    # tempfilename = "JX_165_7_12"
    # tempfilename = "JX_254_5_218"
    # tempfilename = "JX_260_1_74"
    # tempfilename = "JX_245_2_155"
    # tempfilename = "JX_245_3_67"
    # tempfilename = "JX_260_1_126"
    # tempfilename = "JX_245_3_87" # 三列夹注小字
    # tempfilename = "JX_254_5_218"
    # tempfilename = "JX_260_1_206"
    # tempfilename = "JX_260_1_241"
    # tempfilename = "JX_260_1_256"
    # tempfilename = "GL_807_2_8"
    tempfilename = "GL_924_2_35"

    filename = "%s../../tests/data/%s/%s" % (__file__[:-5], tempfilename[:2], tempfilename)
    # 加载字框数据
    with open(filename + ".json", 'r', encoding='UTF-8') as load_f:
        data_dict = json.load(load_f)
        coordinate_char_list = data_dict['chars']
        coordinate_block_list = data_dict['blocks']
        # 加载栏框和列框数据
        # with open(filename + "_column" + ".json", 'r') as load_f:
        # data_dict = json.load(load_f)
        # coordinate_block_list = data_dict['blocks']
        # coordinate_column_list = data_dict['columns']
    #########################################################################

    # 保存数据
    char_list = calc(coordinate_char_list, coordinate_block_list)
    py2json = {}
    py2json['char_list'] = char_list
    json_str = json.dumps(py2json)
    # print(char_list)
    # print(json_str)
    ###################################################################################
    # 以下为显示部分 可以忽略

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    show2(char_list, coordinate_char_list, [n for n in range(0, len(char_list))], ax=ax,
          filename=filename + '_note.jpg')
    show_downconnection(coordinate_char_list, connections, [n for n in range(0, len(char_list))])
    plt.show()

    # print(char_list)
    # 读取图片
    pic = mpimg.imread(filename + ".jpg")
    fig, ax = plt.subplots()
    im = ax.imshow(pic, cmap='gray')
    plt.axis('off')
    show(char_list, coordinate_char_list, [n for n in range(0, len(char_list))], ax=ax, filename=filename + '_note.jpg')

    # fig, ax = plt.subplots()
    # im = ax.imshow(pic, cmap='gray')
    # plt.axis('off')
    for i_b in range(0, len(coordinate_block_list)):
        for i_c in range(0, len(coordinate_char_list)):
            # 统计列内字框的索引
            char_indices_in_column = []
            for i in range(0, len(coordinate_char_list)):
                if char_list[i]['column_id'] == i_c + 1 and char_list[i]['block_id'] == i_b + 1:
                    char_indices_in_column.append(i)
            if len(char_indices_in_column) > 0:
                show_connection(char_list, coordinate_char_list, char_indices_in_column)
            else:
                break
    # plt.savefig(filename+'_lines.jpg', dpi = 300)
    plt.show()


if __name__ == '__main__':
    import json
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg

    test()
