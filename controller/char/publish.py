#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.task.base import TaskHandler


class PublishHandler(TaskHandler):
    task2txt = dict(cluster_proof='ocr_txt', cluster_review='ocr_txt', separate_proof='txt', separate_review='txt')

    def publish_many(self, batch='', task_type='', source='', num=None):
        """ 发布聚类、分类的校对、审定任务 """

        def get_task(ps, cnt, tips=None):
            status = self.STATUS_PUBLISHED
            tk = ''.join([p.get('ocr_txt') or p.get('txt') for p in ps])
            meta = dict(batch=batch, num=num, params=ps, txt_kind=tk, char_count=cnt, type_tips=tips, status=status)
            return self.get_publish_meta(task_type, meta)

        def get_txt(task):
            return ''.join([str(p[field]) for p in task.get('params', [])])

        # 哪个字段
        field = self.task2txt.get(task_type)

        # 统计字频
        counts = list(self.db.char.aggregate([
            {'$match': {'source': source}}, {'$group': {'_id': '$' + field, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
        ]))

        # 去除已发布的任务
        txts = [c['_id'] for c in counts]
        published = list(self.db.task.find({'task_type': task_type, 'num': num, 'params.' + field: {'$in': txts}}))
        if published:
            published = ''.join([get_txt(t) for t in published])
            counts = [c for c in counts if str(c['_id']) not in published]

        # 发布聚类校对-常见字
        counts1 = [c for c in counts if c['count'] >= 50]
        normal_tasks = [
            get_task([dict(ocr_txt=c['_id'], count=c['count'], source=source)], c['count'])
            for c in counts1
        ]
        if normal_tasks:
            self.db.task.insert_many(normal_tasks)
            task_params = [t['params'] for t in normal_tasks]
            self.add_op_log(self.db, 'publish_task', dict(task_type=task_type, task_params=task_params), self.username)

        # 发布聚类校对-生僻字
        counts2 = [c for c in counts if c['count'] < 50]
        rare_tasks = []
        params, total_count = [], 0
        for c in counts2:
            total_count += c['count']
            params.append(dict(ocr_txt=c['_id'], count=c['count'], source=source))
            if total_count > 50:
                rare_tasks.append(get_task(params, total_count, '生僻字'))
                params, total_count = [], 0
        if total_count:
            rare_tasks.append(get_task(params, total_count))
        if rare_tasks:
            self.db.task.insert_many(rare_tasks)
            task_params = [t['params'] for t in normal_tasks]
            self.add_op_log(self.db, 'publish_task', dict(task_type=task_type, task_params=task_params), self.username)

        return dict(published=published, normal_count=len(normal_tasks), rare_count=len(rare_tasks))
