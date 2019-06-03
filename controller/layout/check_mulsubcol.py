# 判断一列内是否存在多个子列
def check_multiple_subcolumns(coordinate, indices):
    for i in range(0, len(indices)):
        for j in range(i + 1, len(indices)):
            if compare_y(coordinate[indices[i]], coordinate[indices[j]]) == 0:
                return 1
    return 0


# 比较两个字框的高度，看是否为同高
# 同高为0，A在B的上侧为-1，A在B的下侧为1
def compare_y(A, B):
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
