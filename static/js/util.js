/**
 * 工具类js
 */

/* SweetAlert2*/
const Swal0 = Swal.mixin({confirmButtonColor: '#b8906f', showConfirmButton: false});
const Swal1 = Swal0.mixin({confirmButtonText: '确定', showConfirmButton: true});
const Swal2 = Swal1.mixin({cancelButtonText: '取消', showCancelButton: true});

function showError(title, text, timer) {
  if ($('.ajax-error').length) { // 在页面提示
    $('.ajax-error').text(text.replace(/[。！]$/, '')).show(200);
    if (timer) setTimeout(() => $('.ajax-error').hide(), timer);
  } else { // sweet alert
    let type = /失败|错误/.test(title) && !/没有发生改变/.test(text) ? 'error' : 'warning';
    Swal0.fire($.extend({title: title, html: text, type: type}, timer ? {timer: timer} : {}));
  }
}

function showWarning(title, text, timer) {
  Swal0.fire($.extend({title: title, html: text, type: 'warning'}, timer ? {timer: timer} : {}));
}

function showSuccess(title, text, timer) {
  Swal0.fire($.extend({title: title, html: text, type: 'success'}, timer ? {timer: timer} : {}));
}

function showTips(title, text, timer, reload) {
  Swal0.fire($.extend({title: title, html: text, type: 'warning'}, timer ? {timer: timer} : {}));
  reload && setTimeout(() => location.reload(), 2000);
}

function showConfirm(title, text, func) {
  return Swal2.fire({title: title, html: text, type: 'warning'}).then(result => result.value && func());
}

/* Bootstrap Alert*/
function bsShow(title, text, type, timer, selector, loading) {
  type = type || 'info';
  selector = selector || '#m-alert';
  $(selector).removeClass('alert-info alert-warning alert-success hide').addClass('alert-' + type);
  $(selector).find('.title').html(title);
  $(selector).find('.text').html(text || '');
  $(selector).find('.loading').toggleClass('hide', !(loading || false));
  timer && setTimeout(() => $(selector).addClass('hide'), timer);
}

function bsLoading(title, text, type, selector) {
  bsShow(title, text, type, null, selector, true);
}

function bsHide() {
  $('#m-alert').addClass('hide');
}

/* URL相关*/
function refresh(timer) {
  setTimeout(() => window.location.reload(), timer || 1000);
}

function goto(url, timer) {
  setTimeout(() => window.location = url, timer || 1000);
}

function getQueryString(name) {
  let reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i');
  let r = window.location.search.substr(1).match(reg);
  return r != null ? unescape(r[2]) : '';
}

function setQueryString(name, value, onlySearch, search) {
  let add = name + '=' + value;
  search = search || location.search;
  if (search.indexOf(name + '=') !== -1) {
    search = search.replace(new RegExp(name + '=.*?(&|$)', 'i'), add + '&');
    search = search.replace(/&$/, '');
  } else if (search) {
    search = '?' + add + '&' + search.substr(1);
  } else {
    search = '?' + add;
  }
  return onlySearch ? search : location.pathname + search;
}

function deleteQueryString(names, url) {
  url = url || location.href;
  names = typeof names === 'string' ? names.split(',') : names;
  names.forEach((name) => url = deleteParam(url, name));
  return url;
}

function toggleQueryString(name, value, show) {
  return show ? setQueryString(name, value) : deleteQueryString(name);
}

function deleteParam(query, name) {
  query = query.replace(new RegExp(name + '=.*?&', 'i'), '');
  query = query.replace(new RegExp('[?&]' + name + '=.*?$', 'i'), '');
  return query;
}

function getAnchor() {
  let p = location.href.search(/#[^\/#]+$/);
  return p > 0 ? location.href.substr(p + 1) : '';
}

function setAnchor(anchor) {
  return location.href.replace(/#[^\/#]+$/, '') + '#' + anchor;
}

function encodeFrom() {
  // 将第一个?替换为&
  let url = location.pathname + location.search.replace('?', '&');
  return url;
  // return deleteParam(url, 'to');
}

function decodeFrom() {
  let from = '';
  let index = location.search.indexOf('from=');
  if (index !== -1) {
    from = location.search.substr(index + 5);
    if (from.indexOf('?') === -1)
      from = from.replace('&', '?');
  }

  return from;
  // return deleteParam(from, 'to');
}


/* 时间相关*/
function toLocalTime(isoTimeStamp) {
  if (typeof isoTimeStamp['$date'] !== 'undefined')
    isoTimeStamp = isoTimeStamp['$date'];
  let times = new Date(isoTimeStamp).toISOString().split('T');
  return times[0] + ' ' + times[1].substr(0, 5);
}

Date.prototype.format = function (fmt) {
  let o = {
    "M+": this.getMonth() + 1,
    "d+": this.getDate(),
    "h+": this.getHours(),
    "m+": this.getMinutes(),
    "s+": this.getSeconds(),
    "q+": Math.floor((this.getMonth() + 3) / 3),
    "S": this.getMilliseconds()
  };
  if (/(y+)/.test(fmt)) {
    fmt = fmt.replace(RegExp.$1, (this.getFullYear() + "").substr(4 - RegExp.$1.length));
  }
  for (let k in o) {
    if (new RegExp("(" + k + ")").test(fmt)) {
      fmt = fmt.replace(RegExp.$1, (RegExp.$1.length === 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
    }
  }
  return fmt;
};

/* localStorage*/
function getStorage(key, defaultValue) {
  let value = localStorage.getItem(key);
  if (value === 'true')
    return true;
  if (value === 'false')
    return false;
  return value || defaultValue
}

function setStorage(key, value, ignoreEmpty) {
  if (value || !ignoreEmpty)
    localStorage.setItem(key, value)
}

/* TEXTAREA高度自适应*/
function resetHeight(element) {
  $(element).css({'height': 'auto'}).height($(element).prop('scrollHeight'));
}
