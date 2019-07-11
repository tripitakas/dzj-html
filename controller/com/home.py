#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

from controller.base import BaseHandler
from controller.helper import get_date_time
from controller.op_type import get_op_name, op_in_recent_trends


class HomeHandler(BaseHandler):
    URL = ['/', '/home']

    def get(self):
        """ 首页 """
        user_id = self.current_user['_id']
        visit_count = self.db.log.count_documents({'create_time': {'$gte': get_date_time('%Y-%m-%d 00:00:00')},
                                                   'user_id': user_id, 'type': 'visit'})
        r = list(self.db.log.find({'user_id': user_id, 'type': {'$in': ['login_ok', 'register']}},
                                  {'create_time': 1}).sort('create_time', -1).limit(2))
        if not r:
            return self.redirect(self.get_login_url())
        last_login = r[0]['create_time'][:16]

        time = get_date_time('%Y-%m-%d 00:00:00', diff_seconds=-86400)
        rs = list(self.db.log.find({'create_time': {'$gte': time}})
                  .sort('create_time', -1).limit(100))
        recent_trends, user_trends = [], {}
        for t in rs:
            time = t['create_time'][:15]
            if not op_in_recent_trends(t['type']) or user_trends.get(t['user_id']) == time:
                continue
            user_trends[t['user_id']] = time
            op_name = get_op_name(t['type'])
            recent_trends.append(dict(time=t['create_time'][11:16], user=t.get('nickname'),
                                      context=op_name))

        self.render('home.html', visit_count=1 + visit_count, last_login=last_login,
                    recent_trends=recent_trends[:7])
