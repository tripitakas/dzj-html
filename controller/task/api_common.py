#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@time: 2018/12/27
"""
import re
from datetime import datetime
from tornado.escape import json_decode
from controller.base import DbError
from controller import errors
from controller.task.base import TaskHandler
import controller.validate  as v


class GetPageApi(TaskHandler):
    URL = '/api/task/page/@task_id'

    def get(self, name):
        """ 获取单个页面数据 """
        try:
            page = self.db.page.find_one(dict(name=name))
            if not page:
                return self.send_error_response(errors.no_object)
            self.send_data_response(page)
        except DbError as e:
            self.send_db_error(e)


class GetPagesApi(TaskHandler):
    URL = '/api/task/pages/@task_type'

    def post(self, task_type):
        """ 获取已就绪的页面列表数据 """
        assert task_type in self.all_task_types()
        try:
            task_status = self.STATUS_READY
            data = self.get_request_data()
            condition = {}
            page_prefix = data.get('page_prefix')
            condition['name'] = {}
            if page_prefix:
                condition['name'].update({'$regex': '^%s.*' % page_prefix.upper()})
            exclude_pages = data.get('exclude_pages')
            if exclude_pages:
                condition['name'].update({'$nin': exclude_pages})
            if not condition['name']:
                del condition['name']
            sub_tasks = self.get_sub_tasks(task_type)
            if sub_tasks:
                condition.update({'$or': [{'%s.%s.status' % (task_type, t): task_status} for t in sub_tasks]})
            else:
                condition.update({'%s.status' % task_type: task_status})
            page_no = int(data['page']) if data.get('page') else 1
            page_size = int(self.config['pager']['page_size'])
            count = self.db.page.find(condition, {'name': 1}).count()
            pages = self.db.page.find(condition, {'name': 1}).limit(page_size).skip(page_size*(page_no-1))
            pages = [p['name'] for p in pages]
            response = {'pages': pages, 'page_size': page_size, 'page_no': page_no, 'total_count': count}
            self.send_data_response(response)
        except DbError as e:
            self.send_db_error(e)

class UnlockTasksApi(TaskHandler):
    URL = '/api/task/unlock/@task_type/@page_prefix'

    def get(self, task_type, prefix=None, returned=False):
        """ 退回全部任务 """
        types = task_type.split('.')
        try:
            # prefix为空找所有页面，prefix为6个以上字符为唯一匹配页面，其他则为页名前缀
            pages = self.db.page.find(dict(name=re.compile('^' + prefix) if len(prefix) < 6 else prefix
                                           ) if prefix else {})
            ret = []
            for page in pages:
                info, unset = {}, {}
                name = page['name']
                for field in page:
                    if field in self.task_types and types[0] in field:
                        self.unlock(page, field, types, info, unset, returned)
                if info or unset:
                    values = {}
                    if info:
                        values['$set'] = info
                    if unset:
                        values['$unset'] = unset
                    r = self.db.page.update_one(dict(name=name), values)
                    if r.modified_count:
                        self.add_op_log('unlock_' + task_type, file_id=str(page['_id']), context=name)
                        ret.append(name)
            self.send_data_response(ret)
        except DbError as e:
            self.send_db_error(e)

    def post(self, task_type, prefix=None):
        """ 由审校者主动退回当前任务 """
        assert prefix and len(prefix) > 5
        page = self.db.page.find_one(dict(name=prefix))
        if not page:
            return self.send_error_response(errors.no_object)
        lock_name = 'lock_' + task_type.split('_')[0]
        locked_type = self.get_obj_property(page, lock_name + '.task_type')
        if locked_type != task_type:
            from_exit = 'exit' in self.request.body_arguments
            if from_exit:
                self.send_data_response([])
            return self.send_error_response(errors.task_changed, page_name=page['name'])
        if self.get_obj_property(page, lock_name + '.picked_user_id') not in [self.current_user['_id'], None]:
            return self.send_error_response(errors.task_locked, page_name=page['name'])
        self.get(task_type, prefix, returned=True)

    def unlock(self, page, task_type, types, info, unset, returned):
        def fill_info(field1):
            info['%s.status' % field1] = self.STATUS_RETURNED if returned else self.STATUS_READY
            info['%s.last_updated_time' % field1] = datetime.now()

        lock_name = 'lock_' + task_type.split('_')[0]
        fields = ['picked_user_id', 'picked_by', 'picked_time', 'finished_time']

        unset[lock_name] = None  # 删除锁定信息
        if self.get_obj_property(page, lock_name + '.jump_from_task'):
            return

        if returned:
            fields.remove('picked_by')  # 在任务管理页面可看到原领取人
        if self.task_types[task_type].get('sub_task_types'):
            for sub_task, v in page[task_type].items():
                if len(types) > 1 and types[1] != sub_task:
                    continue
                if isinstance(v, dict) and v.get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
                    fill_info(task_type + '.' + sub_task)
                    for f in fields:
                        unset[task_type + '.' + sub_task + '.' + f] = None
        if page[task_type].get('status') not in [None, self.STATUS_UNREADY, self.STATUS_READY]:
            fill_info(task_type)
            for f in fields:
                unset[task_type + '.' + f] = None


class PickTaskApi(TaskHandler):
    def pick(self, task_type, name):
        """
        领取任务。
        有两种领取任务方式，通过from参数区分：在任务大厅领取任务，在审校任务或我的任务中跳转到字框编辑等指定任务时直接领取任务。
        :param task_type: 任务类型。比如一级任务block_cut_proof，二级任务text_proof.1
        :param name: 任务名称。如果为空，则任取一个。
        """
        try:
            task_user = task_type + '.picked_user_id'
            task_status = task_type + '.status'
            cur_user = self.current_user['_id']
            lock_name = 'lock_' + task_type.split('_')[0]
            lock_user = lock_name + '.picked_user_id'
            lock_type = lock_name + '.task_type'
            assert re.match('^lock_(block|column|char|text)$', lock_name)

            from_url = self.get_query_argument('from', None)
            jump_from_task = bool(from_url and re.match('/task/(do|my)/', from_url))

            # 不重复领取同一任务 (这两种领取任务方式都会设置 page.lock_<type>.picked_user_id)
            page = self.db.page.find_one({'name': name, lock_user: cur_user, lock_type: task_type})
            if page:
                response = dict(url='/task/do/%s/%s' % (task_type.replace('.', '/'), name), name=name)
                self.send_data_response(response)
                return response

            # 有未完成的任务，不能领新任务
            task_uncompleted = not jump_from_task and self.db.page.find_one({
                task_user: cur_user, task_status: self.STATUS_PICKED
            })
            if task_uncompleted and task_uncompleted['name'] != name:
                url = '/task/do/%s/%s' % (task_type.replace('.', '/'), task_uncompleted['name'])
                return self.error_has_uncompleted(url, task_uncompleted)

            page = self.db.page.find_one({'name': name})
            status = self.get_obj_property(page, task_status)
            picked_by = self.get_obj_property(page, lock_name + '.picked_by')
            picked_task_type = self.get_obj_property(page, lock_type)
            jump_or_edit = jump_from_task or status in [self.STATUS_READY, self.STATUS_PENDING, self.STATUS_FINISHED]

            # 锁定任务
            set_v = {
                lock_name + '.jump_from_task': jump_from_task,
                lock_name + '.task_type': task_type,
                lock_name + '.picked_user_id': cur_user,
                lock_name + '.picked_by': self.current_user['name'],
                lock_name + '.picked_time': datetime.now(),
                lock_name + '.last_updated_time': datetime.now()
            }
            cond = {'name': name, lock_user: None}
            if not jump_from_task:
                cond[task_status] = {'$in': [self.STATUS_OPENED, self.STATUS_RETURNED, self.STATUS_FINISHED]}
                cond[task_user] = {'$in': [None, cur_user]}

            r = self.db.page.update_one(cond, {'$set': set_v})
            if not r.matched_count:
                reason = '页面不存在' if not page else (
                    '已被 %s 领走(%s)' % (picked_by, picked_task_type) if picked_by
                    else '任务状态为 ' + self.task_statuses[status])
                return self.error_picked_by_other_user(from_url, reason)

            # 在任务大厅领取任务，则改变任务状态
            self.add_op_log('pick_' + task_type, file_id=page['_id'], context=name)
            if not jump_or_edit:
                r = self.db.page.update_one(dict(name=name, task_user=None), {
                    '$set': {
                        task_user: cur_user,
                        task_status: self.STATUS_PICKED,
                        task_type + '.picked_by': self.current_user['name'],
                        task_type + '.picked_time': datetime.now(),
                        task_type + '.last_updated_time': datetime.now()
                    }
                })
                assert r.matched_count

            response = dict(url='/task/do/%s/%s' % (task_type.replace('.', '/'), name), name=name)
            self.send_data_response(response)
            return response

        except DbError as e:
            self.send_db_error(e)

    def error_has_uncompleted(self, url, task):
        params = dict(url=url)
        if task and isinstance(task, str):
            params['message'] = task
        elif task:
            params['message'] = task.get('name')
        params['message'] = '您还有未完成的任务(%s)，请继续完成后再领取新的任务' % (params['message'])
        code, message = errors.task_uncompleted[0], '您还有未完成的任务(&s)，请继续完成后再领取新的任务' % ()
        return self.send_error_response((code, message), **params)

    def error_picked_by_other_user(self, url, reason):
        code, message = errors.task_picked
        return self.send_error_response((code, '%s: %s' % (message, reason)), url=url)


class PickCutProofTaskApi(PickTaskApi):
    URL = '/api/task/pick/@box_type_cut_proof/@task_id'

    def get(self, kind, name):
        """ 取切分校对任务 """
        self.pick(kind + '_cut_proof', name)


class PickCutReviewTaskApi(PickTaskApi):
    URL = '/api/task/pick/@box_type_cut_review/@task_id'

    def get(self, kind, name):
        """ 取切分审定任务 """
        self.pick(kind + '_cut_review', name)


class PickTextProofTaskApi(PickTaskApi):
    URL = '/api/task/pick/text_proof([.][123])?/@task_id'

    def get(self, num, name):
        """ 取文字校对任务 """

        # 已领取某个校次的任务则不重复领取
        for i in range(1, 4):
            picked = self.db.page.find_one({'text_proof.%d.picked_user_id' % i: self.current_user['_id']})
            if picked:
                picked = self.pick('text_proof.%d' % i, name)
                if isinstance(picked, dict) and 'name' in picked:
                    return
                assert isinstance(picked, tuple)
                return PickTaskApi.error_has_uncompleted(self, picked[1], picked[2] if len(picked) > 2 else {})

        # 别人领取了某个校次的文字校对任务或审定任务，则不能再领取
        conditions = {'$or': [{'text_proof.%d.status' % i: self.STATUS_PICKED} for i in range(1, 4)] + [
            {'text_review.status': self.STATUS_PICKED}]}
        picked = self.db.page.find_one(conditions)
        if picked:
            return self.send_error_response(errors.task_picked)

        # 没领取则依次领取一个校次的任务
        num = num and int(num[-1])
        for i in ([num] if num else range(1, 4)):
            ret = self.pick('text_proof.%d' % i, name)
            if ret:
                if isinstance(ret, tuple) and ret[0] == 2:
                    continue
                assert isinstance(ret, dict)
                return
        assert isinstance(ret, tuple) and ret[0] == 2
        self.send_error_response(errors.task_changed)

    def error_has_uncompleted(self, url, task_uncompleted):
        return 1, url, task_uncompleted  # 有未完成的任意校次任务，在本类的get中退出循环

    def error_picked_by_other_user(self, url, status):
        return 2, url, status  # 任务已被其它人领取，返回None在本类的get中可换其他校次


class PickTextReviewTaskApi(PickTaskApi):
    URL = '/api/task/pick/text_review/@task_id'

    def get(self, name):
        """ 取文字审定任务 """

        # 别人领取了某个校次的文字校对任务或审定任务，则不能再领取
        conditions = {'$or': [{'text_proof.%d.status' % i: self.STATUS_PICKED} for i in range(1, 4)] + [
            {'text_review.status': self.STATUS_PICKED}]}
        picked = self.db.page.find_one(conditions)
        if picked:
            return self.send_error_response(errors.task_picked)

        self.pick('text_review', name)


class SaveCutApi(TaskHandler):
    def save(self, task_type):
        try:
            data = self.get_request_data()
            assert re.match('^[A-Za-z0-9_]+$', data.get('name'))
            assert task_type in self.cut_task_names()

            page = self.db.page.find_one(dict(name=data['name']))
            if not page:
                return self.send_error_response(errors.no_object)

            status = self.get_obj_property(page, task_type + '.status')
            if status != self.STATUS_PICKED:
                return self.send_error_response(errors.task_changed, reason=page['name'])

            task_user = task_type + '.picked_user_id'
            page_user = self.get_obj_property(page, task_user)
            if page_user != self.current_user['_id']:
                return self.send_error_response(errors.task_locked, reason=page['name'])

            result = dict(name=data['name'])
            self.change_box(result, page, data, task_type)
            if data.get('submit'):
                self.submit_task(result, data, page, task_type)

            self.send_data_response(result)
        except DbError as e:
            self.send_db_error(e)

    def change_box(self, result, page, data, task_type):
        name = page['name']
        boxes = json_decode(data.get('boxes', '[]'))
        box_type = data.get('box_type')
        field = box_type and box_type + 's'
        assert not boxes or box_type and field in page

        if boxes and boxes != page[field]:
            page[field] = boxes
            time_field = '%s.last_updated_time' % task_type
            new_info = {field: boxes, time_field: datetime.now()}
            r = self.db.page.update_one({'name': name}, {'$set': new_info})
            if r.modified_count:
                self.add_op_log('save_' + task_type, file_id=page['_id'], context=name)
                result['box_changed'] = True
                result['updated_time'] = new_info[time_field]


class SaveCutProofApi(SaveCutApi):
    URL = '/api/task/save/@box_type_cut_proof'

    def post(self, kind):
        """ 保存或提交切分校对任务 """
        self.save(kind + '_cut_proof')


class SaveCutReviewApi(SaveCutApi):
    URL = '/api/task/save/@box_type_cut_review'

    def post(self, kind):
        """ 保存或提交切分审定任务 """
        self.save(kind + '_cut_review')
