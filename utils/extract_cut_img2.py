#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 针对对指定的chars，从原图提取chars相关的单字图和列图
@time: 2020-02-25
"""

import json
from controller.char.cut import Cut
from controller.helper import load_config, connect_db


def extract_cut_img(db=None, char_condition=None, chars=None):
    """ 从大图中切图，存放到web_img中，供web访问"""

    cfg = load_config()
    db = db or connect_db(cfg['database'])[0]

    if not chars:
        if not char_condition:
            char_condition = {'img_need_updated': True}
        elif isinstance(char_condition, str):
            char_condition = json.loads(char_condition)
        chars = list(db.char.find(char_condition))

    cut = Cut(db, cfg)
    cut.cut_img(chars)


if __name__ == '__main__':
    import fire

    fire.Fire(extract_cut_img)
