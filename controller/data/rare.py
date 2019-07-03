#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: variant
@time: 2019/7/3
"""

import re
import json
from os import path


def load_rare():
    with open(path.join(path.dirname(__file__), 'gaiji.json'), 'r') as f:
        gaiji = json.load(f)
    rare = {v.get('zzs'): v for v in gaiji.values() if v.get('zzs')}
    return rare


def format_rare(txt):
    def get_char(zzs):
        return rare.get(zzs, {}).get('unicode-char') or rare.get(zzs, {}).get('normal') or zzs

    rare = load_rare()
    regex = r'(\[[+-@*\(\)\/\u2000-\u9FFF]+\])'   # 组字式正则式
    replace = {zzs: get_char(zzs) for zzs in re.findall(regex, txt)}
    for zzs, ch in replace.items():
        txt = txt.replace(zzs, ch)
    return txt


