/**
 * 单字校对js，用于CharTxt UIModule
 * 本js依赖于chars、txtTypes、taskType等公共变量
 */
// 更新文字校对历史
function updateTxtLogs(logs) {
  var html3 = (logs || []).map(function (log) {
    var meta = log.txt ? `<label>原字</label><span>${log.txt}</span><br/>` : '';
    meta += log.nor_txt ? `<label>正字</label><span>${log.nor_txt}</span><br/>` : '';
    meta += log.txt_type ? `<label>类型</label><span>${txtTypes[log.txt_type] || ''}</span><br/>` : '';
    meta += log.remark ? `<label>备注</label><span>${log.remark}</span><br/>` : '';
    meta += log.username ? `<label>校对人</label><span>${log.username}</span><br/>` : '';
    meta += log.create_time ? `<label>创建时间</label><span>${toLocalTime(log.create_time)}</span><br/>` : '';
    meta += log.updated_time ? `<label>更新时间</label><span>${toLocalTime(log.updated_time)}</span><br/>` : '';
    return `<div class="log"><div class="log-meta">${meta}</div></div>`;
  }).join('');
  $('.txt-logs .body').html(html3);
  $('.txt-logs').toggleClass('hide', !html3.length);
}

// 更新切分校对历史
function updateBoxLogs(logs) {
  var html2 = (logs || []).map(function (log) {
    var pos = ['x', 'y', 'w', 'h'].map(function (item) {
      return item + ':' + (log[item] || log.pos[item] || '');
    }).join(', ');
    var meta = log.pos ? `<label>坐标</label><span>${pos}</span><br/>` : '';
    meta += log.username ? `<label>校对人</label><span>${log.username}</span><br/>` : '';
    meta += log.create_time ? `<label>创建时间</label><span>${toLocalTime(log.create_time)}</span><br/>` : '';
    meta += log.updated_time ? `<label>更新时间</label><span>${toLocalTime(log.updated_time)}</span><br/>` : '';
    return `<div class="log"><div class="log-meta">${meta}</div></div>`;
  }).join('');
  $('.box-logs .body').html(html2);
  $('.box-logs').toggleClass('hide', !html2.length);
}

// 更新切分校对历史
function updateBaseInfo(ch) {
  if ($('.base-info').length) {
    $('.base-info .txt').text(ch.txt || '');
    $('.base-info .nor_txt').text(ch.nor_txt || '');
    $('.base-info .txt_type').text(txtTypes[ch.txt_type] || '');
  }
}

// 更新字符编辑面板
function updateCharTxtPanel(ch) {
  // 更新候选字列表
  var html1 = ch.ocr_col && ch.ocr_col !== '■' ? `<span class="txt-item ocr-col${ch.ocr_col === ch.txt ? ' active' : ''}">${ch.ocr_col}</span>` : '';
  html1 += ch.cmp_txt && ch.cmp_txt !== '■' ? `<span class="txt-item cmp-txt${ch.cmp_txt === ch.txt ? ' active' : ''}">${ch.cmp_txt}</span>` : '';
  html1 += (ch.alternatives || '').split('').map(function (c) {
    return `<span class="txt-item${c === ch.txt ? ' active' : ''}">${c}</span>`;
  }).join('');
  $('.txt-alternatives .body').html(html1);
  $('.txt-alternatives').toggleClass('hide', !html1.length);

  // 更新切分校对历史
  updateBoxLogs(ch.box_logs);

  // 更新文字校对历史
  updateTxtLogs(ch.txt_logs);

  // 更新基本信息
  updateBaseInfo(ch);

  // 更新当前参数
  $('#search-variant').val(ch.ocr_txt || ch.txt);
  $('.char-edit .current-name').val(ch.name || ch.page_name + '_' + ch.cid);
  $('.m-footer .char-name').text(ch.name);
  $('.m-footer .page-name').text(ch.page_name);

  // 更新请您校对
  $('.proof .txt').val(ch.txt || ch.ocr_txt);
  $('.proof .nor-txt').val(ch.nor_txt || '');
  $('.proof .remark').val('');
  $('.proof .txt-types :radio').each(function (i, item) {
    $(item).val() === (ch.txt_type || '') ? $(item).prop('checked', true) : $(item).removeAttr('checked');
  });
}

// 点击候选字
$(document).on('click', '.txt-item', function () {
  $('.proof .txt').val($(this).attr('data-value') || $(this).text());
  $('.txt-item.active').removeClass('active');
  $(this).addClass('active');
});

// 提交文字修改
$('#submit-txt').on('click', function () {
  if ($(this).hasClass('disabled')) return;
  var name = $('.char-edit .current-name').val();
  var data = {
    task_type: taskType || '',
    txt: $('.proof .txt').val() || '',
    nor_txt: $('.proof .nor-txt').val() || '',
    txt_type: $('.txt-types :checked').val() || '',
    remark: $('.proof .remark').val() || '',
  };
  postApi('/char/txt/' + name, {data: data}, function (res) {
    if (/char\/[A-Z0-9_]+/.test(location.pathname)) {
      return location.reload();
    }
    location.href = setAnchor(name);
    bsShow('成功！', '已保存成功', 'success', 1000, '#s-alert');
    // 更新chars数据
    if (typeof chars !== 'undefined') {
      data.txt_logs = res.txt_logs;
      chars[name] = $.extend(chars[name], data);
    }
    updateTxtLogs(res.txt_logs);
    updateBaseInfo(chars[name]);
    // 更新字图列表
    var $curItem = $('#' + name);
    if ($curItem.length) {
      $curItem.find('.txt').text(data.txt);
      var index = $curItem.attr('class').search(/proof\d/);
      var no = $curItem.attr('class').substr(index + 5, 1);
      $curItem.removeClass('proof' + no).addClass('proof' + res.txt_logs.length);
    }
  });
});