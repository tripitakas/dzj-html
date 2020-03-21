#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.task.base import TaskHandler


class PublishHandler(TaskHandler):

    def publish_many(self, batch='', task_type=''):
        """ 发布聚类校对、审定任务 """

        def get_task(_task_type, param):
            meta = dict(batch=batch, status=self.STATUS_PUBLISHED, input=param)
            return self.get_publish_meta(_task_type, meta)

        # 统计字频
        counts = list(self.db.char.aggregate([
            {'$match': {'batch': batch}},
            {'$group': {'_id': '$ocr_txt', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]))

        # 发布聚类校对
        counts1 = [c for c in counts if c['count'] >= 50]
        cluster_tasks = [get_task(task_type, dict(ocr_txt=c['_id'], count=c['count'])) for c in counts1]
        self.db.task.insert_many(cluster_tasks)
        self.add_log('publish_task', context='%s,%s,%s' % (batch, task_type, len(cluster_tasks)),
                     username=self.username)

        # 发布僻字校对
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        rare_type = 'rare_proof' if task_type == 'char_proof' else 'rare_review'
        for c in counts2:
            total_count += c['count']
            params.append(dict(ocr_txt=c['_id'], count=c['count']))
            if total_count > 50:
                rare_tasks.append(get_task(rare_type, params))
                params, total_count = [], 0
        self.db.task.insert_many(rare_tasks)
        self.add_log('publish_task', context='%s,%s,%s' % (batch, rare_type, len(rare_tasks)),
                     username=self.username)

        return dict(cluster_count=len(cluster_tasks), rare_count=len(rare_tasks))
