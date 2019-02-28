#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/10/23
"""
import sys

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf-8')


class User(object):
    id = str
    name = str
    email = str
    password = str
    phone = int
    authority = str  # ACCESS_ALL 组合而成，逗号分隔
    gender = str
    image = str
    status = int
    create_time = str
    last_time = str
    old_password = str  # 修改密码临时用
    login_md5 = str  # 密码和权限的MD5码


ACCESS_CUT_PROOF = '切分校对员'
ACCESS_CUT_REVIEW = '切分审定员'
ACCESS_TEXT_PROOF = '文字校对员'
ACCESS_TEXT_REVIEW = '文字审定员'
ACCESS_TEXT_EXPERT = '文字专家'
ACCESS_FMT_PROOF = '格式标注员'
ACCESS_FMT_REVIEW = '格式审定员'
ACCESS_TASK_MGR = '任务管理员'
ACCESS_DATA_MGR = '数据管理员'
ACCESS_MANAGER = '超级管理员'
ACCESS_ALL = [ACCESS_CUT_PROOF, ACCESS_CUT_REVIEW, ACCESS_TEXT_PROOF, ACCESS_TEXT_REVIEW, ACCESS_TEXT_EXPERT,
              ACCESS_FMT_PROOF, ACCESS_FMT_REVIEW, ACCESS_TASK_MGR, ACCESS_DATA_MGR, ACCESS_MANAGER]

authority_map = dict(cut_proof=ACCESS_CUT_PROOF, cut_review=ACCESS_CUT_REVIEW,
                     text_proof=ACCESS_TEXT_PROOF, text_review=ACCESS_TEXT_REVIEW,
                     fmt_proof=ACCESS_FMT_PROOF, fmt_review=ACCESS_FMT_REVIEW,
                     text_expert=ACCESS_TEXT_EXPERT, manager=ACCESS_MANAGER,
                     task_mgr=ACCESS_TASK_MGR, data_mgr=ACCESS_DATA_MGR)


# 下列每种任务类型(按依赖顺序列出任务类型)对应一个任务池，相关状态和用户等字段名以此为前缀
task_types = ['block_cut_proof', 'column_cut_proof', 'char_cut_proof',
              'block_cut_review', 'column_cut_review', 'char_cut_review',
              'text1_proof', 'text2_proof', 'text3_proof', 'text_review',
              'fmt_proof', 'fmt_review', 'hard_proof']
re_task_type = '|'.join(task_types)
task_type_authority = dict(block_cut_proof='cut_proof', column_cut_proof='cut_proof', char_cut_proof='cut_proof',
                           block_cut_review='cut_review', column_cut_review='cut_review', char_cut_review='cut_review',
                           text1_proof='text_proof', text2_proof='text_proof', text3_proof='text_proof')

# 下列任务状态中，发布任务后为opened，如果依赖其他任务条件则为pending，提交任务后为ended，自动触发后续任务为opened
STATUS_OPENED = 'opened'
STATUS_PENDING = 'pending'
STATUS_LOCKED = 'locked'
STATUS_RETURNED = 'returned'
STATUS_ENDED = 'ended'
task_statuses = {STATUS_OPENED: '未领取', STATUS_PENDING: '未就绪', STATUS_LOCKED: '进行中',
                 STATUS_RETURNED: '已退回', STATUS_ENDED: '已完成', None: '未发布'}
