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

function bsAlertWithLoading(title, text, type, selector) {
  bsAlert(title, text, type, null, selector, true);
}

function bsAlert(title, text, type, timer, selector, loading) {
  // type的值为info/warning/success等几种类型
  type = typeof type !== 'undefined' ? type : 'info';
  selector = typeof selector !== 'undefined' ? selector : '#m-alert';
  $(selector).removeClass('alert-info alert-warning alert-success hide').addClass('alert-' + type);
  $(selector).find('.text').text(text);
  $(selector).find('.title').text(title);
  loading = typeof loading !== 'undefined' ? type : false;
  $(selector).find('.loading').toggleClass('hide', !loading);
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