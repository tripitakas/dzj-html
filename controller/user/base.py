#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""

from controller.base import BaseHandler


class UserHandler(BaseHandler):
    pass


# 下列每种任务类型(按依赖顺序列出任务类型)对应一个任务池，相关状态和用户等字段名以此为前缀
task_types = ['block_cut_proof', 'column_cut_proof', 'char_cut_proof',
              'block_cut_review', 'column_cut_review', 'char_cut_review',
              'text_proof.1', 'text_proof.2', 'text_proof.3', 'text_review',
              'fmt_proof', 'fmt_review', 'hard_proof']
re_task_type = '|'.join(task_types).replace('.', r'\.')
re_cut_type = '(block|column|char)_cut_(proof|review)'
task_type_authority = dict(block_cut_proof='cut_proof', column_cut_proof='cut_proof', char_cut_proof='cut_proof',
                           block_cut_review='cut_review', column_cut_review='cut_review', char_cut_review='cut_review',
                           text_proof_1='text_proof', text_proof_2='text_proof', text_proof_3='text_proof')

# 下列任务状态中，发布任务后为opened，如果依赖其他任务条件则为pending，提交任务后为ended，自动触发后续任务为opened
STATUS_OPENED = 'opened'
STATUS_PENDING = 'pending'
STATUS_LOCKED = 'locked'
STATUS_RETURNED = 'returned'
STATUS_ENDED = 'ended'
task_statuses = {STATUS_OPENED: '未领取', STATUS_PENDING: '未就绪', STATUS_LOCKED: '进行中',
                 STATUS_RETURNED: '已退回', STATUS_ENDED: '已完成', None: '未发布'}
