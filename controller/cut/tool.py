import numpy as np


def lis_argsort(seq):
    return sorted(range(len(seq)), key=seq.__getitem__)


def find_same_col(boxes, mark, temp_in_col, thresh):
    adding = True
    while adding:
        adding = False
        for i in range(boxes.shape[0]):
            if not mark[i]:
                left_min = np.min(np.array(temp_in_col)[:, 0])
                right_max = np.max(np.array(temp_in_col)[:, 2])

                same_left = abs(boxes[i, 0] - left_min) <= thresh
                same_right = abs(boxes[i, 2] - right_max) <= thresh
                at_right = boxes[i, 0] - left_min > thresh
                at_left = boxes[i, 2] + thresh < right_max

                if same_left or same_right or (at_right and at_left):
                    temp_in_col.append(boxes[i])
                    mark[i] = True
                    adding = True
    return mark, temp_in_col


def merge_box(col_out):
    # process overlap part
    # input boxes shape(size, 5)( :, min_left, min_top, max_right, max_bt)
    # col_out: length: initial detected col, col_out[i] stores each element(shape: _, 5)
    # boxes: store each col box min_left, max_right, min_top, max_bottom
    # out: length: final col number  (store each bbox fall in the same col)
    out = []
    boxes = [[np.min(c[:, 0]), np.min(c[:, 1]), np.max(c[:, 2]), np.max(c[:, 3])] for c in col_out]
    boxes = np.array(boxes)
    # print(boxes[0], col_out[0], boxes[1], col_out[1])
    mark = dict(zip(range(boxes.shape[0]), [False] * boxes.shape[0]))
    # important trick, sorted by width descending
    col_out = col_out[(boxes[:, 0] - boxes[:, 2]).argsort()]
    boxes = boxes[(boxes[:, 0] - boxes[:, 2]).argsort()]
    # print(boxes[0], col_out[0], boxes[1], col_out[1])

    for i in range(boxes.shape[0]):
        if not mark[i]:
            mark[i] = True
            tmp_chars = col_out[i]
            temp_box = [boxes[i]]
            for j in range(boxes.shape[0]):
                if not mark[j]:
                    left_min = min(np.array(temp_box)[:, 0])
                    right_max = max(np.array(temp_box)[:, 2])
                    if (left_min <= boxes[j][0] and boxes[j][2] <= right_max) \
                            or (boxes[j][0] <= left_min < boxes[j][2] < right_max and (
                                boxes[j][2] - left_min) / (boxes[j][2] - boxes[j][0]) >= 0.6) \
                            or (right_max and left_min < boxes[j][0] < right_max <= boxes[j][2] and (
                                right_max - boxes[j][0]) / (boxes[j][2] - boxes[j][0]) >= 0.6):
                        temp_box.append(boxes[j])  # merge columns
                        mark[j] = True
                        tmp_chars = np.concatenate([tmp_chars, col_out[j]], axis=0)
            out.append(tmp_chars)
    return np.array(out)


def read_col(col_out):
    # col_out: length(number of col in this banmian), col_out[i], detected box fall in this col
    # sorted from right to left
    tmp_left = [min(c[:, 0]) for c in col_out]
    ind = lis_argsort([(-1) * i for i in tmp_left])
    col_out = col_out[np.array(ind)]
    for i in range(len(col_out)):
        # sorted from top to bottom in each column
        col_out[i] = col_out[i][col_out[i][:, 1].argsort()]

    page_small = []
    page_char = []
    for i in range(len(col_out)):
        # each column
        width = max(col_out[i][:, 2]) - min(col_out[i][:, 0])
        center = (max(col_out[i][:, 2]) + min(col_out[i][:, 0])) / 2
        # print(width, ' ', center)
        tmp_small = []
        char_array = []
        for j in range(col_out[i].shape[0]):
            box = col_out[i][j]
            if ((box[3] - box[1]) / width > 0.6
                or (box[1] <= center <= box[3] and box[3] > center and
                    1 / 3 < (center - box[1]) / (box[3] - center) < 3 and
                    (box[3] - box[1]) / width >= 0.5)):
                # mean big character
                if tmp_small:
                    tmp2, char_array = output_small_char(tmp_small, char_array)
                    page_small.append(tmp2)
                    tmp_small = []
                char_array.append(box)
            else:
                tmp_small.append(box)
                if j == col_out[i].shape[0] - 1:
                    tmp2, char_array = output_small_char(tmp_small, char_array)
                    page_small.append(tmp2)

        page_char.append(char_array)

    return page_char, page_small


def output_small_char(tmp_sm, char_array):
    tmp_sm = np.array(tmp_sm)
    mark = dict(zip(range(tmp_sm.shape[0]), [False] * tmp_sm.shape[0]))
    tmp_sm = tmp_sm[(tmp_sm[:, 0] - tmp_sm[:, 2]).argsort()]
    out = []
    for i in range(len(tmp_sm)):
        if not mark[i]:
            mark[i] = True
            temp = [tmp_sm[i]]
            mark, temp = find_same_col(tmp_sm, mark, temp, thresh=5)
            temp = np.array(temp)
            out.append(temp)

    out = np.array(out)
    out = merge_box(out)
    # sorted from right->left
    tmp = []
    for i in range(len(out)):
        tmp.append(min(out[i][:, 0]))
    ind = lis_argsort([(-1) * i for i in tmp])
    out = np.array(out)[np.array(ind)]
    for i in range(len(out)):
        # sorted from top to bottom
        out[i] = out[i][out[i][:, 1].argsort()]

    for i in range(len(out)):
        for j in range(out[i].shape[0]):
            char_array.append(out[i][j])
    return out, char_array


def char_to_line(chars, block):
    cs = np.array([[c['x'], c['y'], c['x'] + c['w'], c['y'] + c['h'], i] for i, c in enumerate(chars)])

    if not block:
        if cs.shape[0] == 0:
            return 0, 0
        boxes = cs[(cs[:, 0] - cs[:, 2]).argsort()]  # sorted by width descending
    else:
        if isinstance(block, dict):
            block = [block['x'], block['y'], block['x'] + block['w'], block['y'] + block['h']]
        assert len(block) == 4, 'invalid block'
        assert block[2] > block[0] and block[3] > block[1], 'invalid block size'
        left = block[0]
        top = block[1]
        right = block[2]
        bt = block[3]

        y_in = np.logical_and(cs[:, 1] + (cs[:, 3] - cs[:, 1]) / 4 > top,
                              cs[:, 3] - (cs[:, 3] - cs[:, 1]) / 4 < bt)
        x_in = np.logical_and(cs[:, 0] + (cs[:, 2] - cs[:, 0]) / 4 > left,
                              cs[:, 2] - (cs[:, 2] - cs[:, 0]) / 4 < right)
        d = np.logical_and(y_in, x_in)
        boxes = cs[np.where(d)]
        if boxes.shape[0] < 1:
            return 0, 0
        boxes = boxes[(boxes[:, 0] - boxes[:, 2]).argsort()]  # sorted by width descending

    mark = dict(zip(range(boxes.shape[0]), [False] * boxes.shape[0]))
    col_out = []
    for i in range(boxes.shape[0]):
        if not mark[i]:
            mark[i] = True
            temp = [boxes[i]]
            # thresh(5 pixel) is the left, right interval between the detected box
            find_same_col(boxes, mark, temp, thresh=5)
            col_out.append(np.array(temp))
    col_out = merge_box(np.array(col_out))

    page_char, page_small = read_col(col_out)
    return page_char, page_small
