// 初始化
$(document).ready(function () {
  getAnchor() ? $('#' + getAnchor()).click() : $('.char-item:first').click();
});

// 更新列图
var paper, rect;

function updateColumnImg(ch) {
  var column = ch.column;
  var columnImg = $('#col-holder');
  var ratio = Math.min(columnImg.height() / column.h, 108 / column.w);
  var imgName = ch['page_name'] + '_' + ch.column.cid;
  rect && rect.remove();
  rect = null;
  if (imgName !== columnImg.attr('data-id')) {
    columnImg.attr('data-id', imgName);
    paper && paper.remove();
    var imgPath = 'columns/' + imgName.split('_').slice(0, -1).join('/') + '/' + imgName + '_' + ch.column.hash + '.jpg';
    var columnUrl = columnBaseUrl.replace(/columns\/.*?.jpg/, imgPath);
    paper = Raphael('col-holder', column.w + 8, column.h + 8).initZoom();
    paper.image(columnUrl, 4, 4, column.w, column.h).initZoom();
    rect = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom()
        .setAttr({stroke: '#158815', 'stroke-width': 0, fill: 'rgba(255, 0, 0, .4)'});
    paper.setZoom(ratio).setSize((column.w + 8) * ratio, (column.h + 8) * ratio);
  } else if (paper) {
    rect = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom(1)
        .setAttr({stroke: '#158815', 'stroke-width': 0, fill: 'rgba(255, 0, 0, .4)'}).setZoom(ratio);
  }
}

// 更新校对记录
function updateLogs(logs) {
  var html = (logs || []).map(function (log) {
    var head = `<span class="log-txt txt-item">${log.txt || log.ori_txt}</span>`;
    var meta = log.txt ? `<label>正字</label><span>${log.txt}</span><br/>` : '';
    meta += log.ori_txt ? `<label>原字</label><span>${log.ori_txt}</span><br/>` : '';
    meta += log.txt_type ? `<label>类型</label><span>${log.txt_type + (txtTypes[log.txt_type] || '')}</span><br/>` : '';
    meta += log.remark ? `<label>备注</label><span>${log.remark}</span><br/>` : '';
    meta += `<label>校对人</label><span>${log.username}</span><br/>`;
    meta += `<label>创建时间</label><span>${toLocalTime(log.create_time)}</span><br/>`;
    meta += `<label>更新时间</label><span>${toLocalTime(log.updated_time)}</span><br/>`;
    return `<div class="log"><div class="log-head">${head}</div><div class="log-meta">${meta}</div></div>`;
  }).join('');
  $('.logs .body').html(html);
  $('.logs').toggleClass('hide', !html.length);
}

function updateWorkPanel(ch) {
  // 更新当前参数
  $('.m-footer .char-name').text(ch.cid);
  $('.m-footer .page-name').text(ch.page_name);
  $('#currentName').val(ch.name || ch.page_name + '_' + ch.cid);
  // 更新OCR候选
  $('.ocr-alternatives .body').html((ch.alternatives || ch.txt || '').split('').map(function (c) {
    return '<span class="ocr-txt txt-item' + (c === ch.txt ? ' active' : '') + '">' + c + '</span>';
  }));
  // 更新校对历史
  updateLogs(ch.txt_logs);
  // 更新请您校对
  $('.proof .remark').val('');
  $('.proof .txt').val(ch.txt || ch.ocr_txt);
  $('.txt-type .radio-item :radio').each(function (i, item) {
    $(item).val() === ch.txt_type ? $(item).prop('checked', true) : $(item).removeAttr('checked');
  });
  // 更新列图和字框
  if ($('#col-holder').length)
    updateColumnImg(ch);
}

// 排序
$('#btn-cc-up').on('click', () => location.href = setQueryString('order', 'cc'));
$('#btn-cc-down').on('click', () => location.href = setQueryString('order', '-cc'));

// 按修改过滤
$('#btn-my-update').on('click', () => location.href = setQueryString('update', 'my'));
$('#btn-all-update').on('click', () => location.href = setQueryString('update', 'all'));

// 按置信度过滤
$('#btn-filter').on('click', function () {
  var start = $('#filter-start').val();
  if (start && start.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showWarning('提示', '起始值不符合要求');
  var end = $('#filter-end').val();
  if (end && end.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showWarning('提示', '终止值不符合要求');
  if (!start.length && !end.length)
    return showWarning('提示', '请输入起始值或终止值');
  if (start.length && !end.length) {
    location.href = setQueryString('cc', '>=' + start);
  } else if (end.length && !start.length) {
    location.href = setQueryString('cc', '<=' + end);
  } else {
    location.href = setQueryString('cc', start + ',' + end);
  }
});

// 点击候选字
var $txt = $('.proof .txt');
$(document).on('click', '.txt-item', function () {
  $txt.val($(this).text() + $txt.val().replace(/[^A-Z*]/, ''));
  $('.txt-item.active').removeClass('active');
  if ($txt.val().indexOf($(this).text()) >= 0) {
    $(this).addClass('active');
  }
});

// 点击文字类型
$('.txt-type .radio-item').click(function () {
  var txtType = $(this).find(':radio').val();
  $txt.val(txtType === '*' ? txtType : $txt.val().replace(/[A-Z*]/g, '') + txtType);
});

// 查看page页面
$('.m-footer .page-name').on('click', function () {
  var cid = $('#currentName').val();
  var pageName = cid.split('_').slice(0, -1).join('_');
  if (cid && pageName)
    window.open('/page/' + pageName + '?txt=off&char_id=' + cid, '_blank');
});

// 查看char页面
$('.m-footer .char-name').on('click', function () {
  window.open('/char/' + $('#currentName').val(), '_blank');
});

// 单击字图
$('.char-panel .char-item').on('click', function () {
  $('.char-items .current').removeClass('current');
  $(this).addClass('current');
  var id = $(this).attr('data-id');
  var ch = chars[id] || {};
  updateWorkPanel(ch);
});

// 提交修改
$('#submit-proof').click(function () {
  var name = $('#currentName').val();
  var data = {
    edit_type: typeof editType !== 'undefined' ? editType : 'raw_edit',
    txt: $('.proof .txt').val(),
    ori_txt: $('.proof .ori-txt').val() || '',
    remark: $('.proof .remark').val()
  };
  postApi('/char/' + name, {data: data}, function (res) {
    updateLogs(res.txt_logs);
    location.href = setAnchor(name);
    data.txt_logs = res.txt_logs;
    if ($('.proof .txt-type :checked').length)
      data.txt_type = $('.proof .txt-type :checked').val();
    // chars[id] = $.extend(chars[id], data);
    var $curItem = $('#' + name);
    $curItem.find('.txt').text($txt.val());
    var index = $curItem.attr('class').search(/proof\d/);
    var no = $curItem.attr('class').substr(index + 5, 1);
    $curItem.removeClass('proof' + no).addClass('proof' + (parseInt(no) + 1));
    bsShow('成功！', '已保存成功', 'success', 1000, '#s-alert');
  });
});