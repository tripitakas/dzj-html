#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 首页
@time: 2018/6/23
"""

import re
import traceback
from controller.base import BaseHandler
from controller.helper import get_date_time
from controller.op_type import get_op_def, op_in_recent_trends, page_kinds
from controller.task.base import TaskHandler


class HomeHandler(BaseHandler):
    URL = ['/', '/home']

    def get(self):
        """ 首页 """
        try:
            user_id = self.current_user['_id']
            visit_count = self.db.log.count_documents({'create_time': {'$gte': get_date_time('%Y-%m-%d 00:00:00')},
                                                       'user_id': user_id, 'type': 'visit'})
            r = list(self.db.log.find({'user_id': user_id, 'type': {'$in': ['login_ok', 'register']}},
                                      {'create_time': 1}).sort('create_time', -1).limit(2))
            last_login = r and r[0]['create_time'][:16] or ''

            time = get_date_time('%Y-%m-%d 00:00:00', diff_seconds=-86400 * 5)
            rs = list(self.db.log.find({'create_time': {'$gte': time}})
                      .sort('create_time', -1).limit(100))
            recent_trends, user_trends = [], {}
            for t in rs:
                if not op_in_recent_trends(t['type']):
                    continue
                # 每个人的操作记录中，忽略一分钟内的连续记录
                time = t['create_time'][:15]  # 15:到分钟
                if user_trends.get(t['user_id']) == time:
                    continue
                user_trends[t['user_id']] = time

                context, params = '', {}
                try:
                    d = get_op_def(t['type'], params)
                    if d:
                        task_type = params.get('task_type')
                        msg = d.get('msg', d['name'])
                        if 'page_kind' in msg:
                            kind = t['context'][:2]
                            msg = msg.replace('{page_kind}', page_kinds.get(kind, kind))
                        if 'page_name' in msg:
                            r = re.findall(r'^([A-Za-z0-9_]+)', t['context'])
                            msg = msg.replace('{page_name}', r and r[0] or '')
                        if 'task_type' in msg:
                            msg = msg.replace('{task_type}', TaskHandler.all_types().get(task_type, task_type))
                        if 'count' in msg:
                            msg = msg.replace('{count}', re.findall(r'^(\d+)', t['context'])[0])
                        if 'context' in msg:
                            msg = msg.replace('{context}', t['context'])
                        context = msg
                except Exception:
                    traceback.print_exc()
                    context = 'err: %s, %s' % (t.get('context'), t['type'])
                recent_trends.append(dict(time=t['create_time'][5:16], user=t.get('nickname'), context=context[:20]))

            self.render('home.html', visit_count=1 + visit_count, last_login=last_login, get_date_time=get_date_time,
                        recent_trends=recent_trends[:7], version=self.application.version)
        except Exception as e:
            self.send_db_error(e, render=True)
