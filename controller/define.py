#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 后端公共定义类
@time: 2019/3/10
"""

task_types = {
    'cut_block_proof': {
        'description': '切栏校对',
    },
    'cut_block_review': {
        'description': '切栏审定',
    },
    'cut_column_proof': {
        'description': '切列校对',
    },
    'cut_column_review': {
        'description': '切列审定',
    },
    'cut_char_proof': {
        'description': '切字校对',
    },
    'cut_char_review': {
        'description': '切字审定',
    },
    'text_proof': {
        'description': '文字校对',
        'sub_task_types': {
            '1': {
                'description': '校一',
            },
            '2': {
                'description': '校二',
            },
            '3': {
                'description': '校三',
            },
            '4': {
                'description': '校四',
            }
        }
    },
    'text_review': {
        'description': '文字审定',
    },
}

url_placeholder = {
    'user_id': r'[A-Za-z0-9_]+',
    'task_id': r'[A-Za-z0-9_]+',
    'sutra_id': r'[a-zA-Z]{2}',
    'num': r'\d+',
}
