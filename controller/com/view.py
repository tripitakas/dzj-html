#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/6/23
"""
from operator import itemgetter
from controller.base import BaseHandler
from datetime import datetime, timedelta
from controller.helper import get_date_time
from controller.task.base import TaskHandler


class HomeHandler(TaskHandler):
    URL = ['/', '/home']

    # 用户希望隐藏自己的名字
    hide_names = ['王伟华']

    def get(self):
        """ 首页"""

        def get_month_star():
            """ 每种任务类型，选出前三名，作为上月校勘之星"""
            # 查找上月之星，如果没有则创建
            now = datetime.now()
            last_month = get_date_time('%Y-%m', now - timedelta(days=now.day + 1))
            stars = self.db.star.find_one({'month': last_month})
            if not stars:
                mt_stars = []
                last_month_end = datetime.strptime(last_month, '%Y-%m')
                this_month_begin = datetime.strptime(get_date_time('%Y-%m'), '%Y-%m')
                cond = {'status': 'finished', 'finished_time': {'$lte': this_month_begin, '$gte': last_month_end}}
                task_types = ['cut_proof', 'cut_review', 'cluster_proof', 'cluster_review']
                for task_type in task_types:
                    cond['task_type'] = task_type
                    counts = list(self.db.task.aggregate([
                        {'$match': cond},
                        {'$group': {'_id': '$picked_user_id', 'count': {'$sum': 1}}},
                        {'$sort': {'count': -1}},
                        {'$limit': 5},
                    ]))
                    for c in counts[:3]:
                        mt_stars.append(dict(task_type=task_type, picked_user_id=c['_id'], count=c['count']))
                self.db.star.insert_one(dict(month=last_month, stars=stars))
            else:
                mt_stars = stars['stars']
            if not mt_stars:
                return []
            # 设置用户名
            user_ids = [s['picked_user_id'] for s in mt_stars]
            user_names = {u['_id']: u['name'] for u in list(self.db.user.find({'_id': {'$in': user_ids}}, {'name': 1}))}
            for star in mt_stars:
                star['username'] = user_names.get(star['picked_user_id']) or ''
                if star['username'] in self.hide_names:
                    star['username'] = star['username'][0] + '*' * (len(star['username']) - 1)
            mt_stars.sort(key=itemgetter('count'), reverse=True)
            return mt_stars[:10]

        def get_time_slot():
            """ 当前时段"""
            hour = get_date_time('%H')
            time_map = [[0, '凌晨'], [5, '早上'], [8, '上午'], [11, '中午'], [13, '下午'], [19, '晚上']]
            for i, t in enumerate(time_map):
                if t[0] >= int(hour):
                    return time_map[i - 1][1]
            return time_map[-1][1]

        def get_task_info(t):
            name = t.get('doc_id') or t.get('txt_kind') or ''
            op = '领取了' if t['status'] == 'picked' else '完成了'
            return '%s %s %s %s' % (t['picked_by'], op, self.get_task_name(t['task_type']), name)

        try:
            # 今日访问次数
            today_begin = datetime.strptime(get_date_time('%Y-%m-%d'), '%Y-%m-%d')
            condition = {'create_time': {'$gte': today_begin}, 'user_id': self.user_id, 'op_type': 'visit'}
            visit_count = self.db.log.count_documents(condition)

            # 最后登录时间
            condition = {'user_id': self.user_id, 'op_type': {'$in': ['login_ok', 'register']}}
            r = list(self.db.log.find(condition).sort('create_time', -1).limit(2))
            last_login = get_date_time(date_time=r[0]['create_time'] if r else None)

            # 我的任务
            my_latest_tasks = self.find_mine(order='-picked_time', page_size=4)
            finished_count = self.count_task(status=self.STATUS_FINISHED, mine=True)
            unfinished_count = self.count_task(status=self.STATUS_PICKED, mine=True)

            # 最新动态
            status = [self.STATUS_PICKED, self.STATUS_FINISHED]
            fields = ['task_type', 'doc_id', 'txt_kind', 'status', 'picked_time', 'finished_time', 'picked_by',
                      'picked_user_id']
            condition = {'task_type': {'$regex': '(cut_|text_|cluster_|rare_)'}, 'status': {'$in': status}}
            latest_tasks = list(self.db.task.find(condition, {k: 1 for k in fields}).sort('picked_time', -1).limit(10))

            # 本月校勘之星
            month_stars = get_month_star()

            # 通知公告
            articles = list(self.db.article.find({'category': '通知', 'active': '是'}, {'content': 0}))

            self.render('com_home.html', version=self.application.version, get_task_info=get_task_info,
                        time_slot=get_time_slot(), visit_count=visit_count + 1, last_login=last_login,
                        my_latest_tasks=my_latest_tasks, finished_count=finished_count,
                        unfinished_count=unfinished_count, latest_tasks=latest_tasks,
                        month_stars=month_stars, articles=articles)

        except Exception as error:
            return self.send_db_error(error)


class CbetaSearchHandler(BaseHandler):
    URL = '/com/search'

    def get(self):
        """ 检索cbeta"""
        self.render('com_search.html')


class PunctuationHandler(BaseHandler):
    URL = '/com/punctuate'

    def get(self):
        """ 自动标点"""
        self.render('com_punctuate.html')
