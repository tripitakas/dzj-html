#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/23
"""
from datetime import datetime
from operator import itemgetter
from controller.base import BaseHandler
from controller.helper import get_date_time
from controller.task.base import TaskHandler


class HomeHandler(TaskHandler):
    URL = ['/', '/home']

    def get(self):
        """ 首页"""

        def get_month_star():
            """ 每种任务类型，选出前三名，作为本月校勘之星 """
            statistic = {k: {} for k in ['cut_proof', 'cut_review', 'text_proof', 'text_review', 'text_hard']}
            for task in month_tasks:
                tsk_type = 'text_proof' if 'text_proof' in task['task_type'] else task['task_type']
                if str(task['picked_user_id']) not in statistic[tsk_type]:
                    statistic[tsk_type][str(task['picked_user_id'])] = [task['picked_by'], 1]
                else:
                    statistic[tsk_type][str(task['picked_user_id'])][1] += 1
            statistic = {k: v for k, v in statistic.items() if v}
            for task_type, v in statistic.items():
                user2count = list(v.values())
                user2count.sort(key=itemgetter(1))
                statistic[task_type] = user2count[0]
            return {self.get_task_name(k): v for k, v in statistic.items() if v}

        def get_time_slot():
            """ 当前时段 """
            hour = get_date_time('%H')
            time_map = [[0, '凌晨'], [5, '早上'], [8, '上午'], [11, '中午'], [13, '下午'], [19, '晚上']]
            for i, t in enumerate(time_map):
                if t[0] >= int(hour):
                    return time_map[i - 1][1]
            return time_map[-1][1]

        def get_task_info(t):
            op = '领取了' if t['status'] == 'picked' else '完成了'
            return '%s %s %s %s' % (t['picked_by'], op, self.get_task_name(t['task_type']), t.get('doc_id'))

        try:
            # 今日访问次数
            user_id = self.current_user['_id']
            today_begin = datetime.strptime(get_date_time('%Y-%m-%d'), '%Y-%m-%d')
            condition = {'create_time': {'$gte': today_begin}, 'user_id': user_id, 'op_type': 'visit'}
            visit_count = self.db.log.count_documents(condition)

            # 最后登录时间
            condition = {'user_id': user_id, 'op_type': {'$in': ['login_ok', 'register']}}
            r = list(self.db.log.find(condition).sort('create_time', -1).limit(2))
            last_login = get_date_time(date_time=r[0]['create_time'] if r else None)

            # 我的任务
            my_latest_tasks = self.find_mine(order='-picked_time', page_size=4)
            finished_count = self.count_task(status=self.STATUS_FINISHED, mine=True)
            unfinished_count = self.count_task(status=self.STATUS_PICKED, mine=True)

            # 最新动态
            status = [self.STATUS_PICKED, self.STATUS_FINISHED]
            fields = ['task_type', 'doc_id', 'status', 'picked_time', 'finished_time', 'picked_by', 'picked_user_id']
            task_types = ['cut_proof', 'cut_review', 'text_proof_1', 'text_proof_2', 'text_proof_3',
                          'text_review', 'text_hard']
            condition = {'task_type': {'$in': task_types}, 'status': {'$in': status}}
            latest_tasks = list(self.db.task.find(condition, {k: 1 for k in fields}).sort('picked_time', -1).limit(10))

            # 本月校勘之星
            status = self.STATUS_FINISHED
            month_begin = datetime.strptime(get_date_time('%Y-%m'), '%Y-%m')
            condition = {'task_type': {'$in': task_types}, 'status': status, 'finished_time': {'$gte': month_begin}}
            month_tasks = list(self.db.task.find(condition, fields))
            month_star = get_month_star()

            # 通知公告
            articles = list(self.db.article.find({'category': '通知', 'active': '是'}, {'content': 0}))

            self.render('com_home.html', version=self.application.version, get_task_info=get_task_info,
                        time_slot=get_time_slot(), visit_count=visit_count + 1, last_login=last_login,
                        my_latest_tasks=my_latest_tasks, finished_count=finished_count,
                        unfinished_count=unfinished_count, latest_tasks=latest_tasks,
                        month_star=month_star, articles=articles)

        except Exception as error:
            return self.send_db_error(error)


class CbetaSearchHandler(BaseHandler):
    URL = '/tool/search'

    def get(self):
        """ 检索cbeta"""
        self.render('com_search.html')


class PunctuationHandler(BaseHandler):
    URL = '/tool/punctuate'

    def get(self):
        """ 自动标点"""
        self.render('com_punctuate.html')
