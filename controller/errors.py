#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc 定义后端API的错误码和数据库常用函数
@time: 2018/10/23
"""

need_login = 403, '尚未登录'
db_error = 10000, '服务访问出错'
mongo_error = 20000, '文档库访问出错'

multiple_errors = 1000, '多个数据校验错误'
not_allowed_empty = 1001, '%s不允许为空'
not_allowed_both_empty = 1002, '%s和%s不允许同时为空'
invalid_name = 1003, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_phone = 1004, '手机号码格式有误'
invalid_email = 1005, '邮箱格式有误'
invalid_password = 1006, '密码应为6至18位由数字、字母和英文符号组成的字符串，不可以为纯数字或纯字母'
invalid_range = 1007, '%s数据范围应为[%s, %s]'
need_phone_or_email = 1008, '没有指定手机或邮箱'
need_password = 1009, '没有指定密码'
invalid_phone_or_email = 1010, '手机或邮箱格式有误'
not_allow_equal = 1011, '%s和%s一致'
not_equal = 1012, '%s和%s不一致'
record_existed = 1013, '%s已存在'
multiple_record = 1014, '%s存在多条记录'
invalid_priority = 1015, '优先级有误'
not_in_list = 1016, '%s应在列表%s中'
code_timeout = 1017, '%s不正确或过期'

no_user = 2001, '没有此账号'
user_existed = 2002, '账号已存在'
incorrect_password = 2003, '密码错误'
incorrect_old_password = 2012, '原始密码错误'
unauthorized = 2004, '没有权限'
auth_changed = 2005, '授权信息已改变，请您重新登录'
no_change = 2006, '没有发生改变'
incomplete = 2007, '信息不全'
invalid_parameter = 2008, '无效参数'
no_object = 2009, '对象不存在或已删除'
cannot_delete_self = 2012, '不能删除自己'
url_not_found = 2013, '路径不存在或没有配置'

task_unauthorized = 3000, '您没有本任务的权限'
task_picked = 3001, '本任务已被领走，请领取新任务'
task_uncompleted = 3002, '您还有未完成的任务，请完成后再领取新任务'
no_task_to_pick = 3003, '目前没有新任务可领取，请关注任务动态'
task_exceed_max = 3004, '任务数量超过上限'
task_not_published = 3005, '任务状态不是已发布'
task_text_proof_duplicated = 3006, '您曾领取过本页面的文字校对任务，不能再领取其它校次任务'
task_return_only_picked = 3007, '只能退回进行中的任务'
task_finished_not_allowed_do = 3008, '任务已完成，不能做任务，可以查看或更新'
task_not_allowed_withdraw = 3009, '只能撤回已发布、等待前置任务或进行中的任务'
task_not_allowed_reset = 3010, '只能重置已就绪的任务'

data_is_locked = 4001, '数据已经被其他人锁定'
data_lock_failed = 4002, '数据锁定失败'
data_unauthorized = 4003, '您没有数据权限'

tripitaka_not_existed = 5001, '藏经不存在'
