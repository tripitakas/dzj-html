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
