#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 发布任务
    1. 任务数据。
    任务依赖的数据由TaskConfig.task_types[task_type].input_field定义，如果不依赖任何数据或该数据已就绪，则可以发布任务。
    2. 前置任务
    默认的前置任务由TaskConfig.task_types[task_type].pre_tasks定义
    管理员在发布任务时，可以自由选择前置任务，任务发布后，该任务的前置任务将记录在数据库中。
    如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则悬挂，状态为“pending”。
    用户领取任务后，状态为“picked”，退回任务后，状态为“returned”，提交任务后，状态为“finished”。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、文档集合（doc_ids）。
@time: 2018/12/27
"""
from datetime import datetime
from controller.task.base import TaskHandler


class PublishBaseHandler(TaskHandler):
    MAX_PUBLISH_RECORDS = 10000  # 用户单次发布任务最大值

    def publish_task(self, task_type, pre_tasks, steps, priority, force, doc_ids):
        """ 发布某个任务类型的任务。
        :return 格式如下：
        { 'un_existed':[...], 'published_before':[...], 'un_ready':[...], 'published':[...], 'pending':[...],
          'publish_failed':[...], 'pending_failed':[...], 'not_published':[...] }
        """
        assert task_type in self.task_types

        log = dict()
        # 检查数据是否存在
        collection, id_name, input_field, shared_field = self.task_meta(task_type)
        docs = list(self.db[collection].find({id_name: {'$in': doc_ids}}))
        log['un_existed'] = set(doc_ids) - set([doc.get(id_name) for doc in docs])
        doc_ids = [doc.get(id_name) for doc in docs]

        # 检查数据是否已就绪
        if doc_ids and input_field:
            log['un_ready'] = [d.get(id_name) for d in docs if not d.get(input_field)]
            doc_ids = set(doc_ids) - set(log['un_ready'])

        # force为False时，检查数据是否已发布。
        # 去掉状态为OPENED\PENDING\PICKED\FINISHED的任务，准备发布其余状态（包括已退回或已撤回）的任务
        if not force and doc_ids:
            ss = [self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED, self.STATUS_FINISHED]
            condition = dict(task_type=task_type, status={'$in': ss}, doc_id={'$in': list(doc_ids)})
            log['published_before'] = set(t.get('doc_id') for t in self.db.task.find(condition, {'doc_id': 1}))
            doc_ids = set(doc_ids) - log['published_before']

        # 发布新任务
        if doc_ids:
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                for t in pre_tasks:
                    assert t in self.task_types

                # 针对前置任务均已完成的情况，发布为OPENED
                condition = dict(task_type={'$in': pre_tasks}, collection=collection, id_name=id_name,
                                 doc_id={'$in': list(doc_ids)}, status=self.STATUS_FINISHED)
                tasks_finished = list(self.db.task.find(condition, {'task_type': 1, 'doc_id': 1}))
                log['published'] = self._select_tasks_which_pre_tasks_all_finished(tasks_finished, pre_tasks)
                pre_tasks = {t: self.STATUS_FINISHED for t in pre_tasks}
                self._publish_task(task_type, self.STATUS_OPENED, priority, pre_tasks, steps, list(log['published']))
                doc_ids = doc_ids - log['published']

                # 其余为前置任务未发布或未全部完成的情况，发布为PENDING
                self._publish_task(task_type, self.STATUS_PENDING, priority, {t: '' for t in pre_tasks}, steps, doc_ids)
                log['pending'] = doc_ids
            else:
                self._publish_task(task_type, self.STATUS_OPENED, priority, {}, steps, doc_ids)
                log['published'] = doc_ids

        return {k: value for k, value in log.items() if value}

    def _publish_task(self, task_type, status, priority, pre_tasks, steps, doc_ids):
        """ 发布新任务 """
        assert task_type in self.task_types
        now = datetime.now()
        steps = {'todo': steps}
        collection, id_name = self.task_meta(task_type)[:2]
        meta = dict(task_type=task_type, collection=collection, id_name=id_name, doc_id='', status=status,
                    priority=int(priority), steps=steps, pre_tasks=pre_tasks, input='', result='',
                    create_time=now, updated_time=now, publish_time=now,
                    publish_user_id=self.current_user['_id'],
                    publish_by=self.current_user['name'])
        tasks = []
        for doc_id in doc_ids:
            task = meta.copy()
            task.update({'doc_id': doc_id})
            tasks.append(task)

        if tasks:
            self.db.task.insert_many(tasks, ordered=False)
            self.add_op_log('publish_' + task_type, context='%d个任务: %s' % (len(doc_ids), ','.join(doc_ids)))

    @staticmethod
    def _select_tasks_which_pre_tasks_all_finished(tasks_finished, pre_tasks_required):
        """ 在已完成的任务列表中，过滤出前置任务全部完成的doc_id"""
        tasks = dict()
        pre_tasks_required = set(pre_tasks_required)
        for task in tasks_finished:
            if task.get('doc_id') not in tasks:
                tasks[task.get('doc_id')] = {task.get('task_type')}
            else:
                tasks[task.get('doc_id')].add(task.get('task_type'))
        doc_ids = [k for k, v in tasks.items() if v == pre_tasks_required]
        return set(doc_ids)
