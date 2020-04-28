// 初始化
$(document).ready(function () {
  getAnchor() ? $('#' + getAnchor()).find('.char-img').click() : $('.char-img:first').click();
});

// 更新列图
var paper, charBox, getBox;

function updateColumnImg(ch) {
  var column = ch.column; // 列框
  var columnImg = $('#col-holder'); // 列框容器DIV
  var ratio = Math.min(columnImg.height() / column.h, 108 / column.w);  // 列图显示比例
  var imgName = ch['page_name'] + '_' + ch.column.cid;  // 列图文件名
  var imgPath = 'columns/' + imgName.split('_').slice(0, -1).join('/') + '/' + imgName + '_' + ch.column.hash + '.jpg';
  var columnUrl = columnBaseUrl.replace(/columns\/.*?.jpg/, imgPath); // 列图URL

  if ($.cut) {
    $.cut.create({
      addDisable: true,
      holder: 'col-holder',
      image: columnUrl,
      width: column.w,
      height: column.h,
      name: imgName,
      chars: [{x: ch.pos.x - column.x, y: ch.pos.y - column.y, w: ch.pos.w, h: ch.pos.h}]
    });
    $.cut.bindKeys();
    getBox = function () {
      var c = $.cut.exportBoxes()[0];
      ch._boxChanged = ch._boxChanged ||
          Math.abs(c.x + column.x - ch.pos.x) > 1 || Math.abs(c.y + column.y - ch.pos.y) > 1 ||
          Math.abs(ch.pos.w - c.w) > 1 || Math.abs(ch.pos.h - c.h) > 1;
      ch.pos.x = c.x + column.x;
      ch.pos.y = c.y + column.y;
      ch.pos.w = c.w;
      ch.pos.h = c.h;
      return ch;
    };
    return;
  }

  charBox && charBox.remove();
  charBox = null;
  if (imgName !== columnImg.attr('data-id')) {  // 列图改变则重新创建，否则只更新字框
    columnImg.attr('data-id', imgName);
    paper && paper.remove();
    paper = Raphael('col-holder', column.w + 8, column.h + 8).initZoom(); // 创建稍大的画板，以便字框部分出界看不见
    paper.image(columnUrl, 4, 4, column.w, column.h).initZoom();
    charBox = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom()
        .setAttr({stroke: '#158815', 'stroke-width': 0, fill: 'rgba(255, 0, 0, .4)'});
    paper.setZoom(ratio).setSize((column.w + 8) * ratio, (column.h + 8) * ratio);
  } else if (paper) {
    charBox = paper.rect(ch.pos.x - column.x + 4, ch.pos.y - column.y + 4, ch.pos.w, ch.pos.h).initZoom(1)
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
  var names = $('#currentName').val().split('_');
  var cid = names.pop(), pageName = names.join('_');
  if (cid && pageName)
    window.open('/page/' + pageName + '?txt=off&cid=' + cid, '_blank');
});

// 查看char页面
$('.m-footer .char-name').on('click', function () {
  window.open('/char/' + $('#currentName').val(), '_blank');
});

// 单击字图
$('.char-panel .char-img').on('click', function () {
  $('.char-items .current').removeClass('current');
  $(this).parent().addClass('current');
  var id = $(this).parent().attr('data-id');
  var ch = chars[id] || {};
  updateWorkPanel(ch);
});

$('.char-panel .char-info').on('click', function () {
  $(this).parent().find(':checkbox').click();
});

// 提交文字修改
$('#submit-txt').on('click', function () {
  var name = $('#currentName').val();
  var data = {
    txt: $('.proof .txt').val(), ori_txt: $('.proof .ori-txt').val() || '',
    remark: $('.proof .remark').val() || '', edit_type: editType,
  };
  postApi('/char/txt/' + name, {data: data}, function (res) {
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


// 提交字框修改
$('#submit-box').on('click', function () {
  var name = $('#currentName').val();
  var data = {'pos': getBox()['pos'], 'edit_type': editType};
  postApi('/char/box/' + name, {data: data}, function (res) {
    bsShow('成功！', '已保存成功', 'success', 1000);
  });
});
