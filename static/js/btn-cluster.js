/**
 @desc 聚类相关操作
 */

//----------------------左侧导航：排序及过滤----------------------
$('#btn-cc-up').on('click', function () {
  location.href = toggleQueryString('order', 'cc', !$(this).hasClass('active'));
});
$('#btn-cc-down').on('click', function () {
  location.href = toggleQueryString('order', '-cc', !$(this).hasClass('active'));
});
$('#btn-lc-up').on('click', function () {
  location.href = toggleQueryString('order', 'lc', !$(this).hasClass('active'));
});
$('#btn-lc-down').on('click', function () {
  location.href = toggleQueryString('order', '-lc', !$(this).hasClass('active'));
});
$('#btn-diff').on('click', function () {
  location.href = toggleQueryString('is_diff', 'true', !$(this).hasClass('active'));
});
$('#btn-un-diff').on('click', function () {
  location.href = toggleQueryString('is_diff', 'false', !$(this).hasClass('active'));
});
$('#btn-required').on('click', function () {
  location.href = toggleQueryString('un_required', 'false', !$(this).hasClass('active'));
});
$('#btn-un-required').on('click', function () {
  location.href = toggleQueryString('un_required', 'true', !$(this).hasClass('active'));
});
$('#btn-vague').on('click', function () {
  location.href = toggleQueryString('is_vague', 'true', !$(this).hasClass('active'));
});
$('#btn-un-vague').on('click', function () {
  location.href = toggleQueryString('is_vague', 'false', !$(this).hasClass('active'));
});
$('#btn-deform').on('click', function () {
  location.href = toggleQueryString('is_deform', 'true', !$(this).hasClass('active'));
});
$('#btn-un-deform').on('click', function () {
  location.href = toggleQueryString('is_deform', 'false', !$(this).hasClass('active'));
});
$('#btn-certain').on('click', function () {
  location.href = toggleQueryString('uncertain', 'false', !$(this).hasClass('active'));
});
$('#btn-uncertain').on('click', function () {
  location.href = toggleQueryString('uncertain', 'true', !$(this).hasClass('active'));
});
$('#btn-has-remark').on('click', function () {
  location.href = toggleQueryString('remark', 'true', !$(this).hasClass('active'));
});
$('#btn-no-remark').on('click', function () {
  location.href = toggleQueryString('remark', 'false', !$(this).hasClass('active'));
});
$('#btn-submitted').on('click', function () {
  location.href = toggleQueryString('submitted', 'true', !$(this).hasClass('active'));
});
$('#btn-un-submitted').on('click', function () {
  location.href = toggleQueryString('submitted', 'false', !$(this).hasClass('active'));
});
$('#btn-un-update').on('click', function () {
  location.href = toggleQueryString('update', 'un', !$(this).hasClass('active'));
});
$('#btn-my-update').on('click', function () {
  location.href = toggleQueryString('update', 'my', !$(this).hasClass('active'));
});
$('#btn-all-update').on('click', function () {
  location.href = toggleQueryString('update', 'all', !$(this).hasClass('active'));
});
$('#btn-other-update').on('click', function () {
  location.href = toggleQueryString('update', 'other', !$(this).hasClass('active'));
});


//----------------------顶部导航----------------------
// 置信度过滤
$('#btn-filter').on('click', function () {
  let start = $('#filter-start').val();
  if (start && start.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showTips('提示', '起始值不符合要求', 3000);
  let end = $('#filter-end').val();
  if (end && end.match(/^(0\.\d+|0|1|1\.0)$/) === null)
    return showTips('提示', '终止值不符合要求', 3000);
  if (!start.length && !end.length)
    return showTips('提示', '请输入起始值或终止值', 3000);
  if (start.length && !end.length) {
    location.href = setQueryString('cc', '>=' + start);
  } else if (end.length && !start.length) {
    location.href = setQueryString('cc', '<=' + end);
  } else {
    location.href = setQueryString('cc', start + ',' + end);
  }
});

// 全部选择
$('#bat-select').on('click', function () {
  $(this).toggleClass('active');
  if ($(this).hasClass('active')) {
    $('.char-check :checkbox').prop('checked', true);
  } else {
    $('.char-check :checkbox').removeAttr('checked');
  }
});
$.mapKey('a', () => $('#bat-select').click());

// 多选模式-鼠标滑选
$('.toggle-multi').on('click', function () {
  $('.toggle-multi').removeClass('active');
  $(this).addClass('active');
  if ($(this).attr('id') === 'do-multi') {
    bsShow('', '鼠标滑选 / 正选 已打开', 'info', 800);
  } else if ($(this).attr('id') === 'de-multi') {
    bsShow('', '鼠标滑选 / 反选 已打开', 'info', 800);
  }
});
$.mapKey('v', () => $('#do-multi').click());
$.mapKey('z', () => $('#de-multi').click());
$.mapKey('x', () => $('#un-multi').click());

// 鼠标滑选
$(document).on('mouseenter', '.char-item', function () {
  let id = $('.toggle-multi.active').attr('id');
  if (id === 'do-multi') {
    $(this).find(':checkbox').prop('checked', true);
  } else if (id === 'de-multi') {
    $(this).find(':checkbox').removeAttr('checked');
  }
});

// 显隐排序过滤
$('#toggle-filter').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterFilterPanel', $(this).hasClass('active'));
  $('#filter-panel').toggleClass('hide', !$(this).hasClass('active'));
});
// 显隐字图信息
$('#toggle-char-info').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterCharInfo', $(this).hasClass('active'));
  $('.char-info, .char-check').toggleClass('hide', !$(this).hasClass('active'));
});
// 显隐字框列图
$('#toggle-column-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterColumnPanel', $(this).hasClass('active'));
  $('.column-panel').toggleClass('hide', !$(this).hasClass('active'));
});
// 显隐校对面板
$('#toggle-proof-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterProofPanel', $(this).hasClass('active'));
  $('.proof-panel').toggleClass('hide', !$(this).hasClass('active'));
});
$.mapKey('1', () => $('#toggle-filter').click());
$.mapKey('2', () => $('#toggle-char-info').click());
$.mapKey('3', () => $('#toggle-column-panel').click());
$.mapKey('4', () => $('#toggle-proof-panel').click());

// 检索异体字
$('#search-variant').on('keydown', function (event) {
  let keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    let q = $(this).val().trim();
    if (q.length) window.open('http://hanzi.lqdzj.cn/variant_search?q=' + q, '_blank');
  }
});
$('#icon-search').on('click', function () {
  let q = $('#search-variant').val().trim();
  if (q.length) window.open('http://hanzi.lqdzj.cn/variant_search?q=' + q, '_blank');
});


//----------------------左侧字图----------------------
// 切换字种
$(document).on('click', '.txt-kind', function () {
  let txt = $(this).attr('data-value') || $(this).text().trim();
  location.href = txt ? deleteParam(setQueryString('txt', txt), 'page') : location.pathname;
});

// 切换字图
$(document).on('click', '.char-items .char-item', function () {
  $('.char-item.current').removeClass('current');
  $(this).addClass('current');
  let ch = $.cluster.status.chars[$(this).attr('id').split('-').pop()];
  $.cluster.switchCurChar(ch);
  $.charTxt.setChar(ch);
});

$('.char-panel .char-info, .char-panel .char-check').on('click', function () {
  $(this).parent().find(':checkbox').click();
});

$('.char-check input').on('click', function (e) {
  e.stopPropagation();
});


//----------------------中间列图----------------------
// 缩小图片
$('#zoom-out').on('click', function () {
  $.box.zoomImg(null, 0.9);
});

// 放大图片
$('#zoom-in').on('click', function () {
  $.box.zoomImg(null, 1.1);
});

// 提交字框修改
$('#submit-box').on('click', function () {
  if ($(this).hasClass('disabled')) return;
  let char = $.cluster.exportSubmitData();
  postApi(`/page/char/box/${char.name}`, {data: {pos: char}}, function (res) {
    bsShow('', '保存成功！', 'info', 1000);
    $.charTxt.setBoxLogs(res['box_logs']);
    $.cluster.status.curChar['box_logs'] = res['box_logs'];
  });
});


//----------------------底部查看----------------------
// 查看page
$('.m-footer .page-name').on('click', function () {
  if ($(this).hasClass('disabled')) return;
  let url = '/page/' + $(this).text();
  let charName = $('.m-footer .char-name').text();
  if (charName && charName.length && charName !== '未选中') {
    url += '?cid=' + charName.split('_').pop();
  }
  window.open(url, '_blank');
});

// 查看char
$('.m-footer .char-name').on('click', function () {
  let charName = $(this).text();
  if ($(this).hasClass('disabled') || charName === '未选中') return;
  window.open('/char/' + charName, '_blank');
});

//----------------------快捷键----------------------
$.mapKey('left', () => $('.char-item.current').prev().find('.char-img').click());
$.mapKey('right', () => $('.char-item.current').next().find('.char-img').click());
