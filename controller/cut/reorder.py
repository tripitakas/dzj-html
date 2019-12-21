from operator import itemgetter
from .tool import *


def char_reorder(chars, blocks=None, sort=True, remove_outside=True, img_file=''):
    columns = []
    if not blocks or len(blocks) == 1:
        blocks = [0]  # 单栏则取为整页范围，避免某些折痕明显的页面识别为窄栏
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
    if sort:
        for i, c in enumerate(chars):
            c['index'] = i
        new_chars = [c for c in chars if c.get('char_no')]
        if len(new_chars) != len(chars):
            print('remove %d(%d - %d) chars in char_reorder %s' % (
                len(chars) - len(new_chars), len(chars), len(new_chars), img_file))
            if not remove_outside:
                new_chars = chars
        new_chars.sort(key=itemgetter('block_no', 'line_no', 'char_no'))
        chars[:] = new_chars

    return columns
