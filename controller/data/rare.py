#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: variant
@time: 2019/7/3
"""

import re
import json
from os import path

_cache = {}


def load_rare():
    if 'rare' not in _cache:
        with open(path.join(path.dirname(__file__), 'gaiji.json'), 'r') as f:
            gaiji = json.load(f)
        _cache['rare'] = {v.get('zzs'): v for v in gaiji.values() if v.get('zzs')}
    return _cache['rare']


def format_rare(txt):
    def get_char(zzs):
        return rare.get(zzs, {}).get('unicode-char') or rare.get(zzs, {}).get('normal') or zzs

    rare = load_rare()
    regex = r'\[[+-@*\(\)\/\u2E80-\U0002FFFF]+\]'   # 组字式正则式
    txt = re.sub(regex, lambda m: get_char(m.group(0)), txt)
    return txt
