/**
 @desc 聚类相关操作
 */

//----------------------顶部导航1：排序及过滤----------------------
$('#btn-cc-up').on('click', () => location.href = setQueryString('order', 'cc'));
$('#btn-cc-down').on('click', () => location.href = setQueryString('order', '-cc'));
$('#btn-lc-up').on('click', () => location.href = setQueryString('order', 'lc'));
$('#btn-lc-down').on('click', () => location.href = setQueryString('order', '-lc'));
$('#btn-diff').on('click', () => location.href = setQueryString('is_diff', 'true'));
$('#btn-un-diff').on('click', () => location.href = setQueryString('is_diff', 'false'));
$('#btn-required').on('click', () => location.href = setQueryString('un_required', 'false'));
$('#btn-un-required').on('click', () => location.href = setQueryString('un_required', 'true'));
$('#btn-vague').on('click', () => location.href = setQueryString('is_vague', 'true'));
$('#btn-un-vague').on('click', () => location.href = setQueryString('is_vague', 'false'));
$('#btn-deform').on('click', () => location.href = setQueryString('is_deform', 'true'));
$('#btn-un-deform').on('click', () => location.href = setQueryString('is_deform', 'false'));
$('#btn-certain').on('click', () => location.href = setQueryString('uncertain', 'false'));
$('#btn-uncertain').on('click', () => location.href = setQueryString('uncertain', 'true'));
$('#btn-has-remark').on('click', () => location.href = setQueryString('remark', 'true'));
$('#btn-no-remark').on('click', () => location.href = setQueryString('remark', 'false'));
$('#btn-submitted').on('click', () => location.href = setQueryString('submitted', 'true'));
$('#btn-un-submitted').on('click', () => location.href = setQueryString('submitted', 'false'));
$('#btn-un-update').on('click', () => location.href = setQueryString('update', 'un'));
$('#btn-my-update').on('click', () => location.href = setQueryString('update', 'my'));
$('#btn-all-update').on('click', () => location.href = setQueryString('update', 'all'));
$('#btn-other-update').on('click', () => location.href = setQueryString('update', 'other'));
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

//----------------------顶部导航2----------------------
// 全部选择
$('#bat-select').on('click', function () {
  $(this).toggleClass('active');
  if ($(this).hasClass('active')) {
    $('.char-check :checkbox').prop('checked', true);
  } else {
    $('.char-check :checkbox').removeAttr('checked');
  }
});

// 多选模式
$('#btn-multi').on('click', function () {
  $(this).toggleClass('active');
  $.cluster.status.multiMode = $(this).hasClass('active');
});

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

// 显隐字图信息
$('#toggle-char-info').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterCharInfo', $(this).hasClass('active'));
  $('.char-info, .cc').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐中间列图
$('#toggle-column-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterColumnPanel', $(this).hasClass('active'));
  $('.column-panel').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐工作面板
$('#toggle-proof-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterProofPanel', $(this).hasClass('active'));
  $('.proof-panel').toggleClass('hide', !$(this).hasClass('active'));
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