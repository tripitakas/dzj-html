#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 发布任务
    任务对应的数据就绪后，需要设置对应的数据状态为已就绪，以便进行任务发布。
    任务发布后，将数据状态设置为已发布。任务退回或回收后，需要将数据状态重置为已就绪，以便重新发布。
@time: 2018/12/27
"""
from datetime import datetime
from controller.task.base import TaskHandler


class PublishTasksHandler(TaskHandler):
    MAX_PUBLISH_RECORDS = 10000  # 用户单次发布任务最大值

    def publish_task(self, task_type, pre_tasks, steps, priority, ids):
        """ 发布某个任务类型的任务。
        :return 格式如下：
        { 'un_existed':[...], 'published_ever':[...], 'un_ready':[...], 'published':[...], 'pending':[...],
          'publish_failed':[...], 'pending_failed':[...], 'not_published':[...] }
        """
        assert task_type in self.task_types

        log = dict()
        # 检查数据是否存在
        d = self.task_types[task_type]['data']
        collection, id_name, input_field, shared_field = d['collection'], d['id'], d['input_field'], d['shared_field']
        docs = self.db[collection].find({id_name: {'$in': ids}})
        doc_ids = [doc.get(id_name) for doc in docs]
        log['un_existed'] = set(ids) - set(doc_ids)

        # 检查数据是否已就绪
        if doc_ids:
            log['un_ready'] = [d.get(id_name) for d in docs if not d.get(input_field)]
            doc_ids = set(doc_ids) - set(log['un_ready'])

        # 检查数据是否已发布。
        # 状态为OPENED\PENDING\PICKED\FINISHED的任务，不可以重新发布新任务
        # 其余状态，包括RETURNED\RETRIEVED的任务，都可以重新发布新任务
        if doc_ids:
            ss = [self.TASK_OPENED, self.TASK_PENDING, self.TASK_PICKED, self.TASK_FINISHED]
            condition = dict(task_type=task_type, status={'$in': ss}, id_value={'$in': doc_ids})
            log['published_ever'] = set(t.get('id_value') for t in self.db.task.find(condition, {'id_value': 1}))
            doc_ids = doc_ids - log['published_ever']

        # 发布新任务
        if doc_ids:
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                for t in pre_tasks:
                    assert t in self.task_types

                # 针对前置任务未完成的情况（只要有一个未完成即可），发布为PENDING
                condition = dict(task_type={'$in': pre_tasks}, collection=collection, id_name=id_name,
                                 id_value={'$in': doc_ids}, status={"$ne": self.TASK_FINISHED})
                log['published'] = set(t.get('id_value') for t in self.db.task.find(condition, {'id_value': 1}))
                self._publish_task(task_type, self.TASK_PENDING, priority, pre_tasks, steps, log['published'])
                doc_ids = doc_ids - log['published']

                # 其余为前置任务已完成的情况，发布为OPENED
                self._publish_task(task_type, self.TASK_OPENED, priority, pre_tasks, steps, doc_ids)
                log['pending'] = doc_ids
            else:
                self._publish_task(task_type, self.TASK_OPENED, priority, pre_tasks, steps, doc_ids)
                log['published'] = doc_ids

        return {k: value for k, value in log.items() if value}

    def _publish_task(self, task_type, status, priority, pre_tasks, steps, id_values):
        """ 发布新任务 """
        assert task_type in self.task_types
        task_data = self.task_types[task_type]['data']
        collection, id_name = task_data['collection'], task_data['id']
        meta = dict(task_type=task_type, collection=collection, id_name=id_name, id_value='', status=status,
                    priority=int(priority), steps=dict(todo=steps), pre_tasks={t: '' for t in pre_tasks},
                    input='', result='', created_time=datetime.now(), updated_time=datetime.now(),
                    publish_time=datetime.now(), publish_user_id=self.current_user['_id'],
                    publish_by=self.current_user['name'])
        tasks = []
        for id_value in id_values:
            task = meta.copy()
            task.update({'id_value': id_value})
            tasks.append(task)

        self.db.task.insert_many(tasks, ordered=False)
        self.add_op_log('publish_' + task_type, context='%d个任务: %s' % (len(id_values), ','.join(id_values)))
