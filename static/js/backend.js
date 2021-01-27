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
    showError('失败', data.message || obj.message || '', 3000);
  } || console.log.bind(console);

  if (data && typeof data.data === 'object') {
    data.data = JSON.stringify(data.data);
  }
  data = data || {};

  url = url.substr(0, 4) === '/api' ? url : '/api' + url;
  let args = {
    url: url,
    type: type,
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
      let code = xhr.status || xhr.code || 500;
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
    let type = settings.type;
    if (type !== 'GET' && type !== 'HEAD' && type !== 'OPTIONS') {
      let pattern = /(.+; *)?_xsrf *= *([^;" ]+)/;
      let xsrf = pattern.exec(document.cookie);
      if (xsrf) {
        jqXHR.setRequestHeader('X-Xsrftoken', xsrf[2]);
      }
    }
  }
});

// 将tornado在网页中输出的对象串转为JSON对象，toHTML为true时只做网页解码
function decodeJSON(s, toHTML) {
  let HTML_DECODE = {'&lt;': '<', '&gt;': '>', '&nbsp;': ' ', '&amp;': '&', '&quot;': '"'};
  s = s.replace(/&\w+;|&#(\d+);/g, function ($0, $1) {
    let c = HTML_DECODE[$0];
    if (c === undefined) {
      if (!isNaN($1)) { // Entity Number
        c = String.fromCharCode(($1 === 160) ? 32 : $1);
      } else {  // Not Entity Number
        c = $0;
      }
    }
    return c;
  });
  if (toHTML) return s;
  s = s.replace(/: True/g, ': 1').replace(/: (False|None)/g, ': 0').replace(/\\/g, '/');
  return parseJSON(s);
}

// parseJSON中eval函数需要调用ObjectId函数
function ObjectId(id) {
  return id;
}

// parseJSON中eval函数需要调用datetime.datetime函数
let datetime = {
  datetime: function (year, month, day, hour, minute, second, milli) {
    return year + '-' + (month + '-').padStart(3, '0') + (day + ' ').padStart(3, '0')
        + (hour + ':').padStart(3, '0') + (minute + ':').padStart(3, '0') + (second + '').padStart(2, '0');
  },
};

function parseJSON(s) {
  try {
    s = eval("(" + s + ")");
    if ('_id' in s && '$oid' in s['_id'])
      s['_id'] = s['_id']['$oid'];
    return s
  } catch (e) {
    console.info('invalid JSON: ' + s);
  }
}

// bootstrap相关
$("[data-toggle='tooltip']").tooltip();
$('body').on('click', '[data-stopPropagation]', (e) => e.stopPropagation());

// 帮助
$('#help').on('click', () => $('#helpModal').modal());

// 关闭提示
$('.alert .close').on('click', function () {
  $(this).parent().addClass('hide');
});

// 离开页面
function leave() {
  let url = typeof from !== 'undefined' ? from : decodeFrom();
  if (url === '1') url = getStorage('from');
  url ? window.location = url : window.history.back();
}


