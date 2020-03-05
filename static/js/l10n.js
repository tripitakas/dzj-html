/**
 * 本地化
 */

function _t(key) {
  return key in l10n ? l10n[key] : key;
}

var l10n = {
  un_existed: '数据存在',
  un_ready: '数据未就绪',
  published_before: '任务曾被发布',
  finished_before: '任务已经完成',
  data_level_unqualified: '数据等级不够',
  data_is_locked: '数据被锁定',
  published: '任务发布成功',
  pending: '等待前置任务',
  unauthorized: '用户无权访问',
  un_published: '状态不是已发布',
  duplicated_text: '文字校对重复',
  picked_before: '曾经领过的任务',
  lock_failed: '数据锁定失败',
  assigned: '任务指派成功',
};

