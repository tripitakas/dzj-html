#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@desc 定义后端API的错误码和数据库常用函数
@time: 2018/10/23
"""

need_login = 403, '尚未登录'
db_error = 10000, '服务访问出错'
mongo_error = 20000, '文档库访问出错'

no_object = 1000, '对象不存在'
not_allowed_empty = 1001, '%s不允许为空'
not_allowed_both_empty = 1002, '%s和%s不允许同时为空'
invalid_name = 1003, '姓名应为2~5个汉字，或3~20个英文字母（可含空格和-）'
invalid_phone = 1004, '手机号码格式有误'
invalid_email = 1005, '邮箱格式有误'
invalid_password = 1006, '密码应为6至18位由数字、字母和英文符号组成的字符串，不可以为纯数字或纯字母'
invalid_range = 1007, '%s数据范围应为[%s, %s]'
need_phone_or_email = 1008, '没有指定手机或邮箱'
invalid_phone_or_email = 1009, '手机或邮箱格式有误'
need_password = 1010, '没有指定密码'
both_times_equal = 1011, '%s和%s一致'
not_equal = 1012, '%s和%s不一致'
doc_existed = 1013, '%s已存在'
doc_not_existed = 1014, '%s不存在'
invalid_priority = 1015, '优先级有误'
should_in_list = 1016, '%s应在列表%s中'
code_wrong_or_timeout = 1017, '%s不正确或过期'
invalid_digit = 1018, '数字格式有误'
invalid_tripitaka_code = 1019, '藏编码格式有误'
invalid_volume_code = 1020, '册编码格式有误'
invalid_sutra_code = 1021, '经编码格式有误'
invalid_reel_code = 1022, '卷编码格式有误'
invalid_article_id = 1023, '文章id长度至少为6'
multiple_errors = 1999, '多个数据校验错误'

no_user = 2000, '用户不存在'
user_existed = 2001, '账号已存在'
incorrect_password = 2002, '密码错误'
incorrect_old_password = 2003, '原始密码错误'
unauthorized = 2005, '没有权限'
auth_changed = 2006, '授权信息已改变，请您重新登录'
not_changed = 2007, '没有发生改变'
cannot_delete_self = 2008, '不能删除自己'
url_not_config = 2009, 'Auth中没有配置路径'
verify_failed = 2010, '验证服务失败'
email_send_failed = 2011, '邮件发送失败'
username_duplicated = 2012, '用户名重复，请用手机或邮箱登录'

task_not_existed = 3000, '任务不存在'
task_unauthorized = 3001, '没有任务相应的权限'
task_uncompleted = 3002, '您还有未完成的任务，请完成后再领取新任务'
no_task_to_pick = 3003, '目前没有新任务可领取，请关注任务动态'
task_count_exceed = 3004, '任务数量超过上限'
task_not_published = 3005, '任务状态不是已发布'
task_submit_error = 3021, '列框有增减'
group_task_duplicated = 3006, '您已领取本组任务中的一个，不能重复领取'
task_has_been_picked = 3007, '本任务已被其他人锁定，您没有修改权限'
task_failed = 3010, '任务执行失败'
task_type_error = 3011, '任务类型有误'
task_step_error = 3012, '步骤参数有误'
task_status_error = 3013, '任务状态有误'
statistic_type_error = 3014, '统计类型有误'
box_un_ready = 3015, '切分数据未就绪'
box_not_covered = 3016, '切分框覆盖不完整'
doc_id_not_equal = 3017, '数据ID不一致'
box_not_identical = 3018, '切分信息不一致'
cid_not_identical = 3019, '字框有增减'
col_not_identical = 3020, '列框有增减'

data_level_unqualified = 4001, '数据等级不够'
data_point_unqualified = 4002, '任务积分不够'

img_unavailable = 5001, '图片尚未就绪'
page_code_error = 5002, '页面编码有误'
field_error = 5004, '字段有误'
code_duplicated = 5005, '编码重复'
code_existed = 5006, '编码已存在'
upload_fail = 5100, '上传失败'

invalid_txt = 6001, '文字格式有误'
variant_exist = 6002, '异体字已存在'

oss_not_readable = 7001, 'OSS不可读'
oss_not_writeable = 7002, 'OSS不可写'
no_my_cloud = 7003, 'OSS网盘没有配置'