#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 发布任务
    1. 任务数据已就绪
    已就绪有两种情况：1. 任务不依赖任何数据；2. 任务依赖的数据已就绪，所依赖数据字段由
    TaskConfig.task_types[task_type].input_field定义。
    2. 前置任务
    默认的前置任务由TaskConfig.task_types[task_type].pre_tasks定义
    管理员在发布任务时，可以自由选择前置任务，任务发布后，该任务的前置任务将记录在数据库中。每个任务都可以独立设置自己的前置任务。
    如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则检查前置任务的状态，如果前置任务均已完成，则发布为“opened”，
    如果前置任务有一个未完成，则发布为“pending”。用户完成任务时，将检查并更新后置任务的任务状态。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、文档集合（doc_ids）。
    可以发布已就绪、已退回、已撤回的任务。不可以发布已发布、悬挂或进行中的任务。已完成的任务，根据参数，也可以重新发布。
@time: 2018/12/27
"""
from datetime import datetime
from controller.task.base import TaskHandler


class PublishBaseHandler(TaskHandler):
    MAX_PUBLISH_RECORDS = 10000  # 用户单次发布任务最大值

    def publish_task(self, task_type, pre_tasks, steps, priority, force, doc_ids):
        """ 发布某个任务类型的任务。
        :return 格式如下：
        { 'un_existed':[...], 'un_ready':[...], 'published_before':[...], 'finished':[...],
            'published':[...], 'pending':[...]}
        """
        assert task_type in self.task_types

        log = dict()
        # 检查数据是否存在
        collection, id_name, input_field, shared_field = self.get_task_meta(task_type)
        docs = list(self.db[collection].find({id_name: {'$in': doc_ids}}))
        log['un_existed'] = set(doc_ids) - set([doc.get(id_name) for doc in docs])
        doc_ids = [doc.get(id_name) for doc in docs]

        # 检查数据是否已就绪
        if doc_ids and input_field:
            log['un_ready'] = [d.get(id_name) for d in docs if not d.get(input_field)]
            doc_ids = set(doc_ids) - set(log['un_ready'])

        # 去掉已发布和进行中的任务
        if doc_ids:
            ss = [self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED]
            condition = dict(task_type=task_type, status={'$in': ss}, doc_id={'$in': list(doc_ids)})
            log['published_before'] = set(t.get('doc_id') for t in self.db.task.find(condition, {'doc_id': 1}))
            doc_ids = set(doc_ids) - log['published_before']

        # 去掉已完成的任务（如果不重新发布）
        if not force and doc_ids:
            condition = dict(task_type=task_type, status=self.STATUS_FINISHED, doc_id={'$in': list(doc_ids)})
            log['finished'] = set(t.get('doc_id') for t in self.db.task.find(condition, {'doc_id': 1}))
            doc_ids = set(doc_ids) - log['finished']

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
        collection, id_name = self.get_task_meta(task_type)[:2]
        meta = dict(task_type=task_type, collection=collection, id_name=id_name, doc_id='', status=status,
                    priority=int(priority), steps=steps, pre_tasks=pre_tasks, input=None, result={},
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
            self.add_op_log('publish_' + task_type, context='发布了%d个任务: %s' % (len(doc_ids), ','.join(doc_ids)))

    @staticmethod
    def _select_tasks_which_pre_tasks_all_finished(tasks_finished, pre_tasks):
        """ 在已完成的任务列表中，过滤出前置任务全部完成的doc_id"""
        tasks = dict()
        pre_tasks = set(pre_tasks)
        for task in tasks_finished:
            if task.get('doc_id') not in tasks:
                tasks[task.get('doc_id')] = {task.get('task_type')}
            else:
                tasks[task.get('doc_id')].add(task.get('task_type'))
        doc_ids = [k for k, v in tasks.items() if v == pre_tasks]
        return set(doc_ids)