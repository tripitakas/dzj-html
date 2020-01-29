from .tool import *
from .v2 import calc


def char_reorder(chars, blocks=None, columns_force=None, sort=True, remove_outside=True, img_file=''):
    columns = []
    blocks = blocks or [0]
    if not chars:
        return []
    for c in chars:
        c['block_no'] = c['line_no'] = c['char_no'] = c['no'] = c['char_id'] = 0

    for i, block in enumerate(blocks):
        blk_char, blk_small = char_to_line(chars, block)
        if blk_char:
            for j, column in enumerate(blk_char):
                # means current column
                cur_column = np.array(column)
                left = int(np.min(cur_column[:, 0]))
                top = int(np.min(cur_column[:, 1]))
                right = int(np.max(cur_column[:, 2]))
                bt = int(np.max(cur_column[:, 3]))

                val = {'x': left, 'y': top, 'w': right - left, 'h': bt - top,
                       'block_no': i + 1, 'line_no': j + 1, 'no': j + 1,
                       'column_id': 'b%dc%d' % (i + 1, j + 1), 'txt': ''}
                columns.append(val)
                for ci, c in enumerate(column):
                    char = chars[int(c[4])]
                    char.update(dict(block_no=i + 1, line_no=j + 1, char_no=ci + 1, no=ci + 1,
                                     char_id='b%dc%dc%d' % (i + 1, j + 1, ci + 1)))
                    val['txt'] += char.get('txt', '')
                if not val['txt']:
                    val.pop('txt')
    if sort:
        for i, c in enumerate(chars):
            c['index'] = i
        new_chars = [c for c in chars if c.get('char_no')]
        if len(new_chars) != len(chars):
            print('remove %d(%d - %d) chars in char_reorder %s' % (
                len(chars) - len(new_chars), len(chars), len(new_chars), img_file))
            if not remove_outside:
                new_chars = chars
        sort_chars(new_chars, columns, columns_force or len(blocks) > 1 and [
            dict(x=b[0], y=b[1], w=b[2] - b[0], h=b[3] - b[1]) for b in blocks] or [])
        chars[:] = new_chars
        for c in chars:
            c['cid'] = c.get('cid') or max(int(c1.get('cid', 0)) for c1 in chars) + 1

    return columns_force or columns


def sort_chars(chars, columns, blocks):
    """根据坐标对字框排序和生成编号"""
    ids0 = {}
    new_chars = calc(chars, blocks if len(blocks) > 1 else [dict(x=0, y=0, w=10000, h=10000)], columns)
    assert len(new_chars) == len(chars)
    for c_i, c in enumerate(new_chars):
        if not c['column_order']:
            zero_key = 'b%dc%d' % (c['block_id'], c['column_id'])
            ids0[zero_key] = ids0.get(zero_key, 100) + 1
            c['column_order'] = ids0[zero_key]
        chars[c_i]['char_id'] = 'b%dc%dc%d' % (c['block_id'], c['column_id'], c['column_order'])
        chars[c_i]['block_no'] = c['block_id']
        chars[c_i]['line_no'] = c['column_id']
        chars[c_i]['char_no'] = chars[c_i]['no'] = c['column_order']
