/**
 * Added by Zhang Yungui on 2018/12/18.
 */

/**
 * 调用后端接口
 * @param url 以“/”开头的地址
 * @param type POST 或 GET
 * @param data 数据对象
 * @param success_callback 成功回调函数，参数为 data 对象或数组
 * @param error_callback 失败回调函数，参数为 data 对象或数组
 * @param is_file 是否传输文件
 */
function ajaxApi(url, type, data, success_callback, error_callback, is_file) {
  error_callback = error_callback || Swal0 && function (obj) {
    showError('操作失败', data.message || obj.message || '');
  } || console.log.bind(console);

  if (data && typeof data.data === 'object') {
    data.data = JSON.stringify(data.data);
  }
  data = data || {};

  var args = {
    type: type,
    url: '/api' + url,
    cache: false,
    crossDomain: true,
    xhrFields: {withCredentials: true},
    success: function (data) {
      if (data.status === 'failed') {
        error_callback && error_callback(data);
      } else {
        $.extend(data, data.data && typeof data.data === 'object' && !Array.isArray(data.data) ? data.data : {});
        success_callback && success_callback(data);
      }
    },
    error: function (xhr) {
      var code = xhr.status || xhr.code || 500;
      if (code >= 200 && code <= 299) {
        success_callback && success_callback({});
      } else if (!window.unloading) {
        error_callback({code: code, message: '网络访问失败，不能访问后台服务(' + code + ')'});
      }
    }
  };

  if (typeof is_file !== 'undefined' && is_file) {
    args['data'] = data;
    args['processData'] = false;
    args['contentType'] = false;
  } else {
    args['data'] = $.param(data);
    args['dataType'] = 'json';
  }

  $.ajax(args);
}

/**
 * 以GET方式调用后端接口
 * @param url 以“/”开头的地址，不带 /api
 * @param success 成功回调函数，可选，参数为 data 对象或数组
 * @param error 失败回调函数，可选，参数为 msg、code
 */
function getApi(url, success, error) {
  ajaxApi(url, 'GET', null, success, error);
}

/**
 * 以POST方式调用后端接口
 * @param url 以“/”开头的地址，不带 /api
 * @param data 请求体JSON对象
 * @param success 成功回调函数，可选，参数为 data 对象或数组
 * @param error 失败回调函数，可选，参数为 msg、code
 * @param is_file 是否为文件
 */
function postApi(url, data, success, error, is_file) {
  ajaxApi(url, 'POST', data, success, error, is_file);
}

/**
 * 以POST方式调用后端接口
 * @param url 以“/”开头的地址，不带 /api
 * @param data 请求体JSON对象
 * @param success 成功回调函数，可选，参数为 data 对象或数组
 * @param error 失败回调函数，可选，参数为 msg、code
 */
function postFile(url, data, success, error) {
  ajaxApi(url, 'POST', data, success, error, true);
}

$.ajaxSetup({
  beforeSend: function (jqXHR, settings) {
    var type = settings.type;
    if (type !== 'GET' && type !== 'HEAD' && type !== 'OPTIONS') {
      var pattern = /(.+; *)?_xsrf *= *([^;" ]+)/;
      var xsrf = pattern.exec(document.cookie);
      if (xsrf) {
        jqXHR.setRequestHeader('X-Xsrftoken', xsrf[2]);
      }
    }
  }
});

var HTML_DECODE = {'&lt;': '<', '&gt;': '>', '&nbsp;': ' ', '&amp;': '&', '&quot;': '"'};

// 将tornado在网页中输出的对象串转为JSON对象，toHTML为true时只做网页解码
function decodeJSON(s, toHTML) {
  s = s.replace(/&\w+;|&#(\d+);/g, function ($0, $1) {
    var c = HTML_DECODE[$0];
    if (c === undefined) {
      if (!isNaN($1)) { // Entity Number
        c = String.fromCharCode(($1 === 160) ? 32 : $1);
      } else {  // Not Entity Number
        c = $0;
      }
    }
    return c;
  });
  s = toHTML ? s : s.replace(/'/g, '"').replace(/: True/g, ': 1').replace(/: (False|None)/g, ': 0').replace(/\\/g, '/');
  return toHTML ? s : parseJSON(s);
}

function parseJSON(s) {
  try {
    s = JSON.parse(s);
    if ('_id' in s && '$oid' in s['_id'])
      s['_id'] = s['_id']['$oid'];
    return s
  } catch (e) {
    console.info('invalid JSON: ' + s);
  }
}

// 激活bootstrap tooltip
$(function () {
  $("[data-toggle='tooltip']").tooltip();
});

// bootstrap alert
$(".alert .close").on('click', function () {
  $(this).parent().addClass('hide');
});
/**
 * 工具类js
 */

let defaultTool = 'bs'; // 默认提示工具
const Swal0 = Swal.mixin({confirmButtonColor: '#b8906f', showConfirmButton: false});
const Swal1 = Swal0.mixin({confirmButtonText: '确定', showConfirmButton: true});
const Swal2 = Swal1.mixin({cancelButtonText: '取消', showCancelButton: true});

function showError(title, text, timer) {
  // 在页面提示
  if ($('.ajax-error').length) {
    $('.ajax-error').text(text.replace(/[。！]$/, '')).show(200);
    return setTimeout(() => $('.ajax-error').hide(), timer);
  }
  // bootstrap提示
  if (defaultTool === 'bs' && $('#m-alert').length)
    return bsAlert(title, text, 'warning', timer);
  // sweetalert2提示
  var type = /失败|错误/.test(title) ? 'error' : 'warning';
  Swal0.fire({title: title, html: text, type: type, timer: timer});
}

function showWarning(title, text, timer) {
  if (defaultTool === 'bs' && $('#m-alert').length)
    return bsAlert(title, text, 'warning', timer);
  Swal0.fire({title: title, html: text, type: 'warning', timer: timer});
}

function showSuccess(title, text, timer) {
  if (defaultTool === 'bs' && $('#m-alert').length)
    return bsAlert(title, text, 'success', timer);
  Swal0.fire({title: title, html: text, type: 'success', timer: timer});
}

function showTips(title, text, timer, reload) {
  if (defaultTool === 'bs' && $('#m-alert').length) {
    bsAlert(title, text, 'info', timer);
  } else {
    Swal0.fire({title: title, html: text, type: 'info', timer: timer});
  }
  if (typeof reload !== 'undefined' && reload)
    setTimeout(() => location.reload(), 1000);
}

function swConfirm(title, text, func) {
  return Swal2.fire({title: title, html: text, type: 'warning'}).then(result => result.value && func());
}

function bsAlert(title, text, type, timer, selector, progress) {
  // type的值为info/warning/success等几种类型
  type = typeof type !== 'undefined' ? type : 'info';
  selector = typeof selector !== 'undefined' ? selector : '#m-alert';
  $(selector).removeClass('alert-info alert-warning alert-success hide').addClass('alert-' + type);
  $(selector).find('.text').text(text);
  $(selector).find('.title').text(title);
  progress = typeof progress !== 'undefined' ? type : false;
  $(selector).find('.loading').toggleClass('hide', progress);
  timer && setTimeout(() => $(selector).addClass('hide'), timer);
}

/* URL相关*/
function refresh(timer) {
  timer = typeof timer !== 'undefined' ? timer : 1000;
  setTimeout(() => window.location.reload(), timer);
}

function goto(url, timer) {
  timer = typeof timer !== 'undefined' ? timer : 1000;
  setTimeout(() => window.location = url, timer);
}

function getQueryString(name) {
  var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i');
  var r = window.location.search.substr(1).match(reg);
  if (r != null) {
    return unescape(r[2]);
  }
  return '';
}

function setQueryString(name, value, onlySearch) {
  var search = location.search;
  var add = name + '=' + value;
  if (search.indexOf(name + '=') !== -1) {
    search = search.replace(new RegExp(name + '=.*?(&|$)', 'i'), add + '&');
    search = search.replace(/&$/, '');
  } else if (search) {
    search = '?' + add + '&' + search.substr(1);
  } else {
    search = '?' + add;
  }
  if (typeof onlySearch !== 'undefined' && onlySearch)
    return search;
  else
    return location.pathname + search;
}

function deleteQueryString(names) {
  var url = location.href;
  if (typeof names === 'string')
    names = names.split(',');
  names.forEach(function (name) {
    url = deleteParam(url, name);
  });
  return url;
}

function deleteParam(query, name) {
  query = query.replace(new RegExp(name + '=.*?&', 'i'), '');
  query = query.replace(new RegExp('[?&]' + name + '=.*?$', 'i'), '');
  return query;
}

function getAnchor() {
  var p = location.href.search(/#[^\/#]+$/);
  return p > 0 ? location.href.substr(p + 1) : '';
}

function setAnchor(anchor) {
  return location.href.replace(/#[^\/#]+$/, '') + '#' + anchor;
}

function encodeFrom() {
  // 将第一个?替换为&，然后删除to/page等参数
  var url = location.pathname + location.search.replace('?', '&');
  return deleteParam(url, 'to');
}

function decodeFrom() {
  var from = '';
  var index = location.search.indexOf('from=');
  if (index !== -1) {
    from = location.search.substr(index + 5);
    if (from.indexOf('?') === -1)
      from = from.replace('&', '?');
  }
  return deleteParam(from, 'to');
}

/* 时间相关*/
function toLocalTime(isoTimeStamp) {
  if (typeof isoTimeStamp['$date'] !== 'undefined')
    isoTimeStamp = isoTimeStamp['$date'];
  var times = new Date(isoTimeStamp).toISOString().split('T');
  return times[0] + ' ' + times[1].substr(0, 5);
}
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
  txt: '原字',
  normal_txt: '正字',
  txt_type: '文字类型',
  create_time: '创建时间',
  updated_time: '更新时间',
  remark: '备注',
};

