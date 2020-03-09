/**
 * 工具类js
 */

const Swal0 = Swal.mixin({confirmButtonColor: '#b8906f', showConfirmButton: false});
const Swal1 = Swal0.mixin({confirmButtonText: '确定', showConfirmButton: true});
const Swal2 = Swal1.mixin({cancelButtonText: '取消', showCancelButton: true});

function showError(title, text, timer) {
  // 在页面提示
  if ($('.ajax-error').length) {
    $('.ajax-error').text(text.replace(/[。！]$/, '')).show(200);
    return setTimeout(() => $('.ajax-error').hide(), 5000);
  }
  // 没有错误
  var type = /失败|错误/.test(title) ? 'error' : 'warning';
  if (text === '没有发生改变')
    return showSuccess(title.replace(/失败|错误/, '跳过'), text);
  // 弹框提示
  if (typeof timer !== 'undefined')
    return Swal0.fire({title: title, html: text, type: type, timer: 5000});
  Swal0.fire({title: title, html: text, type: type});
}

function showWarning(title, text, timer) {
  if (typeof timer !== 'undefined')
    Swal0.fire({title: title, html: text, type: 'warning', timer: 5000});
  else
    Swal0.fire({title: title, html: text, type: 'warning'});
}

function showSuccess(title, text, timer) {
  timer = typeof timer === 'undefined' ? 1000 : timer;
  Swal0.fire({title: title, html: text, type: 'success', timer: timer});
}

function showConfirm(title, text, func) {
  return Swal2.fire({title: title, html: text, type: 'warning'}).then(result => result.value && func());
}

function showTips(title, text, reload, timer) {
  if (typeof reload !== 'undefined' && reload) {
    Swal0.fire({title: title, html: text, type: 'success'}, () => window.location.reload());
  } else if (typeof timer !== 'undefined') {
    Swal0.fire({title: title, html: text, timer: timer});
  } else {
    Swal0.fire({title: title, html: text});
  }
}

function bsAlert(title, text, type, hide, selector) {
  // type的值为info/warning/success等几种类型
  type = typeof type !== 'undefined' ? type : 'info';
  hide = typeof hide !== 'undefined' ? hide : true;
  selector = typeof selector !== 'undefined' ? selector : '#bs-alert';
  $(selector).attr('class', 'alert alert-' + type);
  $(selector).find('.text').text(text);
  $(selector).find('.title').text(title);
  if (hide)
    setTimeout(() => $('#bs-alert').addClass('hide'), 1000);
}

function toLocalTime(isoTimeStamp) {
  if (typeof isoTimeStamp['$date'] !== 'undefined')
    isoTimeStamp = isoTimeStamp['$date'];
  var times = new Date(isoTimeStamp).toISOString().split('T');
  return times[0] + ' ' + times[1].substr(0, 5);
}

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
