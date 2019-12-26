#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc: 发布任务
    1. 任务数据已就绪
    已就绪有两种情况：1. 任务不依赖任何数据；2. 任务依赖的数据已就绪，所依赖数据字段由
    Task.task_types[task_type].input_field定义。
    2. 前置任务
    默认的前置任务由TaskConfig.task_types[task_type].pre_tasks定义
    管理员在发布任务时，可以自由选择前置任务，任务发布后，该任务的前置任务将记录在数据库中。每个任务都可以独立设置自己的前置任务。
    如果没有前置任务，则直接发布，状态为“opened”；如果有前置任务，则检查前置任务的状态，如果前置任务均已完成，则发布为“opened”，
    如果前置任务有一个未完成，则发布为“pending”。用户完成任务时，将检查并更新后置任务的任务状态。
    3. 发布任务
    一次只能发布一种类型的任务，发布参数包括：任务类型、前置任务（可选）、优先级、文档集合（doc_ids）。
    可以发布已就绪、已退回的任务。不可以发布已发布、悬挂或进行中的任务。已完成的任务，根据参数，也可以重新发布。
@time: 2018/12/27
"""
from datetime import datetime
from controller.task.base import TaskHandler


class PublishBaseHandler(TaskHandler):
    MAX_PUBLISH_RECORDS = 10000  # 用户单次发布任务最大值

    def publish_many(self, task_type, pre_tasks, steps, priority, force, doc_ids, batch=None):
        """ 发布某个任务类型的任务。
        :return 格式如下：
            {'un_existed':[], 'un_ready':[], 'published_before':[], 'finished_before':[],
            'data_is_locked':[], 'lock_level_unqualified':[], 'published':[], 'pending':[]}
        """
        log = dict()
        assert task_type in self.task_types
        collection, id_name, input_field, shared_field = self.get_task_data_conf(task_type)

        # 去掉不存在的数据
        docs = list(self.db[collection].find({id_name: {'$in': doc_ids}}))
        log['un_existed'] = set(doc_ids) - set([doc.get(id_name) for doc in docs])
        doc_ids = [doc.get(id_name) for doc in docs]

        # 去掉未就绪的数据
        if doc_ids and input_field:
            log['un_ready'] = [d.get(id_name) for d in docs if not d.get(input_field)]
            doc_ids = set(doc_ids) - set(log['un_ready'])

        # 去掉已发布和进行中的任务
        if doc_ids:
            status = [self.STATUS_OPENED, self.STATUS_PENDING, self.STATUS_PICKED]
            condition = dict(task_type=task_type, status={'$in': status}, doc_id={'$in': list(doc_ids)})
            log['published_before'] = set(t.get('doc_id') for t in self.db.task.find(condition, {'doc_id': 1}))
            doc_ids = set(doc_ids) - log['published_before']

        # 去掉已完成的任务（如果不重新发布）
        if not force and doc_ids:
            status = [self.STATUS_FINISHED]
            condition = dict(task_type=task_type, status={'$in': status}, doc_id={'$in': list(doc_ids)})
            log['finished_before'] = set(t.get('doc_id') for t in self.db.task.find(condition, {'doc_id': 1}))
            output_field = self.prop(self.task_types, '%s.data.output_field' % task_type)
            if output_field:  # output_field不为空表示任务已完成
                log['finished_before'].update([d[id_name] for d in docs if d.get(output_field)])
            doc_ids = set(doc_ids) - log['finished_before']

        # 去掉数据锁已分配给其它任务或者数据等级不够的任务
        if doc_ids and shared_field:
            log['data_is_locked'], log['lock_level_unqualified'] = self._check_lock(task_type, doc_ids)
            doc_ids = set(doc_ids) - log['data_is_locked'] - log['lock_level_unqualified']

        # 剩下的，发布新任务
        if doc_ids:
            if pre_tasks:
                pre_tasks = [pre_tasks] if isinstance(pre_tasks, str) else pre_tasks
                # 针对前置任务均已完成的情况，发布为OPENED
                finished_tasks = list(self.db.task.find(
                    {'collection': collection, 'id_name': id_name, 'status': self.STATUS_FINISHED,
                     'doc_id': {'$in': list(doc_ids)}, 'task_type': {'$in': pre_tasks}},
                    {'task_type': 1, 'doc_id': 1}
                ))
                published = self._select_tasks_which_pre_tasks_all_finished(finished_tasks, pre_tasks)
                pre_tasks_status = {t: self.STATUS_FINISHED for t in pre_tasks}
                self._publish_tasks(task_type, self.STATUS_OPENED, priority, pre_tasks_status, steps, published, batch)
                log['published'] = published
                doc_ids = doc_ids - set(log['published'])

                # 其余为前置任务未发布或未全部完成的情况，发布为PENDING
                pre_tasks_status = {t: '' for t in pre_tasks}
                self._publish_tasks(task_type, self.STATUS_PENDING, priority, pre_tasks_status, steps, doc_ids, batch)
                log['pending'] = doc_ids
            else:
                self._publish_tasks(task_type, self.STATUS_OPENED, priority, {}, steps, doc_ids, batch)
                log['published'] = doc_ids

        return {k: value for k, value in log.items() if value}

    def _check_lock(self, task_type, doc_ids):
        """ 检查数据锁是否已分配给其它任务或数据等级是否小于当前数据等级"""
        data_is_locked, lock_level_unqualified = set(), set()
        collection, id_name, input_filed, shared_field = self.get_task_data_conf(task_type)
        conf_level = self.prop(self.data_auth_maps, '%s.level.%s' % (shared_field, task_type), 0)
        docs = self.db[collection].find({id_name: {'$in': list(doc_ids)}}, {'lock': 1, id_name: 1})
        for doc in list(docs):
            lock = self.prop(doc, 'lock.' + shared_field, {})
            level = int(self.prop(doc, 'lock.level.' + shared_field, 0))
            if lock and self.prop(lock, 'is_temp') is False:
                data_is_locked.add(doc[id_name])
            elif conf_level < level:
                lock_level_unqualified.add(doc[id_name])
        return data_is_locked, lock_level_unqualified

    def _publish_tasks(self, task_type, status, priority, pre_tasks, steps, doc_ids, batch):
        """ 发布新任务 """

        def get_meta(doc_id):
            return dict(task_type=task_type, batch=batch, collection=collection, id_name=id_name, doc_id=doc_id,
                        status=status, priority=int(priority), steps={'todo': steps}, pre_tasks=pre_tasks,
                        input=None, result={}, create_time=now, updated_time=now, publish_time=now,
                        publish_user_id=self.current_user['_id'],
                        publish_by=self.current_user['name'])

        now = datetime.now()
        collection, id_name = self.get_task_data_conf(task_type)[:2]
        pre_tasks = {t: '' for t in pre_tasks} if isinstance(pre_tasks, list) else pre_tasks
        tasks = [get_meta(d) for d in doc_ids]
        if tasks:
            self.db.task.insert_many(tasks, ordered=False)
            self.add_op_log('publish_' + task_type, context='发布了%d个任务: %s' % (len(doc_ids), ','.join(doc_ids)))

    @staticmethod
    def _select_tasks_which_pre_tasks_all_finished(tasks_finished, pre_tasks):
        """ 在已完成的任务列表中，过滤出前置任务全部完成的任务"""
        tasks = dict()
        pre_tasks = set(pre_tasks)
        for task in tasks_finished:
            if task.get('doc_id') not in tasks:
                tasks[task.get('doc_id')] = {task.get('task_type')}
            else:
                tasks[task.get('doc_id')].add(task.get('task_type'))
        doc_ids = [k for k, v in tasks.items() if v == pre_tasks]
        return doc_ids
