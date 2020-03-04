#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 针对对指定的chars，从原图提取chars相关的单字图和列图
@time: 2020-02-25
"""

import json
from controller.char.cut import Cut
from controller.helper import load_config, connect_db


def extract_cut_img(db=None, condition=None, chars=None, regen=True):
    """ 从大图中切图，存放到web_img中，供web访问"""

    cfg = load_config()
    db = db or connect_db(cfg['database'])[0]

    if not chars:
        if not condition:
            condition = {'img_need_updated': True}
        elif isinstance(condition, str):
            condition = json.loads(condition)
        chars = list(db.char.find(condition))

    # chars = list(db.char.find({'id': 'GL_1056_5_6_8'}))
    cut = Cut(db, cfg, regen=regen)
    log = cut.cut_img(chars)
    if log.get('success'):
        update = {'has_img': True, 'img_need_updated': False}
        db.char.update_many({'id': {'$in': log['success']}}, {'$set': update})

    print(log)


if __name__ == '__main__':
    import fire

    fire.Fire(extract_cut_img)
