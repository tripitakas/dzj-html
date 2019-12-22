/**
 * Added by Zhang Yungui on 2018/12/18.
 */
swal.setDefaults({confirmButtonColor: '#b8906f'});

function showError(title, text, timer) {
  // 在页面提示
  var $err = $('.ajax-error');
  if ($err.length) {
    $err.text(text.replace(/[。！]$/, '')).show(200);
    return setTimeout(function () {
      $err.hide();
    }, 6000);
  }
  // 没有错误
  if (text === '没有发生改变')
    return showSuccess(title.replace(/失败|错误/, '跳过'), text);
  // 弹框提示
  var type = /失败|错误/.test(title) ? 'error' : 'warning';
  if (typeof timer !== 'undefined')
    swal({
      title: title, text: text, type: type, showConfirmButton: false, html: true,
      allowOutsideClick: true, timer: 6000
    });
  else
    swal({
      title: title, text: text, type: type, html: true, confirmButtonText: '确定',
      showConfirmButton: true
    });
}

function showWarning(title, text) {
  showError(title, text, 'warning');
}

function showSuccess(title, text, timer) {
  timer = typeof timer === 'undefined' ? 1000 : timer;
  swal({title: title, text: text, type: 'success', timer: timer, showConfirmButton: false});
}

function showConfirm(title, text, func) {
  var info = {
    type: 'warning', title: title, text: text, confirmButtonText: '确定', cancelButtonText: '取消',
    showCancelButton: true, closeOnConfirm: false
  };
  return swal(info, func);
}

function showTips(title, text, reload) {
  if (typeof reload !== 'undefined' && reload) {
    swal({title: title, text: text, type: 'success', confirmButtonText: '确定', showConfirmButton: true, html: true},
        function () {
          window.location.reload();
        });
  } else {
    swal({title: title, text: text, type: 'info', html: true, showConfirmButton: false, allowOutsideClick: true});
  }
}

function refresh(timer) {
  timer = typeof timer !== 'undefined' ? timer : 1000;
  setTimeout(function () {
    window.location.reload();
  }, timer);
}

function goto(url, timer) {
  timer = typeof timer !== 'undefined' ? timer : 1000;
  setTimeout(function () {
    window.location = url;
  }, timer);
}

function getQueryString(name) {
  var reg = new RegExp('(^|&)' + name + '=([^&]*)(&|$)', 'i');
  var r = window.location.search.substr(1).match(reg);
  if (r != null) {
    return unescape(r[2]);
  }
  return null;
}

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
  error_callback = error_callback || window.swal && function (obj) {
    showError('操作失败', data.message || obj.message || '');
  } || console.log.bind(console);

  if (data && typeof data.data === 'object') {
    data.data = JSON.stringify(data.data);
  }
  data = data || {};

  var args = {
    url: '/api' + url,
    type: type,
    xhrFields: {
      withCredentials: true
    },
    crossDomain: true,
    cache: false,
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

var HTML_DECODE = {
  '&lt;': '<',
  '&gt;': '>',
  '&amp;': '&',
  '&nbsp;': ' ',
  '&quot;': '"'
};

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
