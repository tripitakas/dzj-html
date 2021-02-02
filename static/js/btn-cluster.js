/**
 @desc 聚类相关操作
 */
//----------------------快捷键----------------------
$.mapKey('a', () => $('#bat-select').click());
$.mapKey('v', () => $('#do-multi').click());
$.mapKey('z', () => $('#de-multi').click());
$.mapKey('x', () => $('#un-multi').click());
$.mapKey('1', () => $('#toggle-filter-panel').click());
$.mapKey('2', () => $('#toggle-char-variant').click());
$.mapKey('3', () => $('#toggle-char-cc').click());
$.mapKey('4', () => $('#toggle-column-panel').click());
$.mapKey('5', () => $('#toggle-proof-panel').click());
$.mapKey('6', () => $('#toggle-proof-info').click());
$.mapKey('.', () => $('.pagers .p-next a').click());
$.mapKey(',', () => $('.pagers .p-prev a').click());
$.mapKey('w', () => $('#page-submit').click());
$.mapKey('v', () => $('.char-txt .btn-submit').click());
$.mapKey('esc', () => $('#btn-reset').click());
$.mapKey('g', () => $('#search-variant').focus());
$.mapKey('enter', () => $('#search-variant').click());
$.mapKey('left', () => $('.char-item.current').prev().find('.char-img').click());
$.mapKey('right', () => $('.char-item.current').next().find('.char-img').click());


//----------------------初始化----------------------
function togglePanels(init) {
  $('#toggle-filter-panel').toggleClass('active', init ? true : getStorage('clusterFilterPanel', true));
  $('.m-panel').toggleClass('hide', init ? false : !getStorage('clusterFilterPanel', true));
  $('#toggle-char-variant').toggleClass('active', init ? true : getStorage('clusterCharVariant', true));
  $('.char-panel .variants').toggleClass('hide', init ? false : !getStorage('clusterCharVariant', true));
  $('#toggle-char-cc').toggleClass('active', init ? true : getStorage('clusterCharCc', true));
  $('.char-panel .char-info').toggleClass('hide', init ? true : getStorage('clusterCharCc', true));
  $('#toggle-column-panel').toggleClass('active', init ? true : getStorage('clusterColumnPanel', true));
  $('.column-panel').toggleClass('hide', init ? false : !getStorage('clusterColumnPanel', true));
  $('#toggle-proof-panel').toggleClass('active', init ? true : getStorage('clusterProofPanel', true));
  $('.proof-panel').toggleClass('hide', init ? false : !getStorage('clusterProofPanel', true));
  $('#toggle-proof-info').toggleClass('active', init ? true : getStorage('clusterProofInfo', true));
  $('.char-panel').toggleClass('hide-mark', init ? false : !getStorage('clusterProofInfo', true));
}

function toggleFilters() {
  let btns = ['order', 'sc', 'is_vague', 'is_deform', 'uncertain', 'remark', 'submitted', 'updated'];
  btns.forEach((q) => getQueryString(q) && $(`#${q}-${getQueryString(q)}`).addClass('active'));
}


//----------------------顶部导航----------------------
// 显隐排序过滤
$('#toggle-filter-panel').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterFilterPanel', $(this).hasClass('active'));
  $('.m-panel').toggleClass('hide', !$(this).hasClass('active'));
});
// 显隐异体字列表
$('#toggle-char-variant').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterCharVariant', $(this).hasClass('active'));
  $('.char-panel .variants').toggleClass('hide', !$(this).hasClass('active'));
});
// 显隐字符置信度
$('#toggle-char-cc').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterCharCc', $(this).hasClass('active'));
  $('.char-panel .char-info').toggleClass('hide', $(this).hasClass('active'));
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
// 显隐校对信息
$('#toggle-proof-info').on('click', function () {
  $(this).toggleClass('active');
  setStorage('clusterProofInfo', $(this).hasClass('active'));
  $('.char-panel').toggleClass('hide-mark', !$(this).hasClass('active'));
});

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

// 鼠标滑选
$(document).on('mouseenter', '.char-item', function (e) {
  if (e.altKey) {
    $(this).find(':checkbox').prop('checked', true);
  } else if (e.shiftKey) {
    $(this).find(':checkbox').removeAttr('checked');
  }
});

// 多选模式-鼠标滑选
$('.toggle-multi2').on('click', function () {
  $('.toggle-multi').removeClass('active');
  $(this).addClass('active');
  if ($(this).attr('id') === 'do-multi') {
    bsShow('', '鼠标滑选 / 正选 已打开', 'info', 800);
  } else if ($(this).attr('id') === 'de-multi') {
    bsShow('', '鼠标滑选 / 反选 已打开', 'info', 800);
  }
});

// 检索异体字或编码
$('#search-variant').on('keydown', function (e) {
  let keyCode = e.keyCode || e.which;
  if (keyCode !== 13) return;
  $('.m-header .icon-search').click();
});
$('.m-header .icon-search').on('click', function () {
  let q = $('#search-variant').val().trim();
  if (!q.length) {
    browse(deleteQueryString('name'));
  } else if (/[a-zA-Z]{2}[0-9_]*/.test(q)) { // 检索编码
    browse(deleteQueryString('page', setQueryString('name', q)));
  } else { // 检索异体字
    $.cluster.loadVariants(q, true);
  }
});


//----------------------左侧导航（排序及过滤）及翻页----------------------
function trimUrl(href) {
  ['http://', 'https://', location.host, /(do|update|nav|browse)\//].forEach((s) => href = href.replace(s, ''));
  return href;
}

function browse(href) {
  postApi(trimUrl(href), {data: {}}, function (res) {
    $.cluster.setChars(res.data.chars);
    $.cluster.updatePager(res.data.pager);
    window.history.pushState({}, null, href);
  });
}

// 去掉排序过滤
$('#btn-reset').on('click', function () {
  let txt = getQueryString('txt');
  let href = location.pathname + (txt.length ? `?txt=${txt}` : '');
  browse(href);
});

$('.pagers').on('click', 'a', function (e) {
  if (!$.cluster.status.ajax) return;
  e.preventDefault();
  let page = $(this).text().trim(), $parent = $(this).parent();
  if ($parent.hasClass('p-first')) page = '1';
  else if ($parent.hasClass('p-last')) page = $('.pagers .page-count').text();
  else if ($parent.hasClass('p-prev')) page = parseInt($('.pagers .active').text()) - 1;
  else if ($parent.hasClass('p-next')) page = parseInt($('.pagers .active').text()) + 1;
  if (page == (getQueryString('page') || '1')) return;
  browse(setQueryString('page', page));
});

$('.pagers .page-no').unbind('keydown').bind('keydown', function (e) {
  let keyCode = e.keyCode || e.which, page = $(this).val().trim();
  if (keyCode !== 13 || !page.length) return;
  e.preventDefault();
  if (page === (getQueryString('page') || '1')) return;
  let href = setQueryString('page', page);
  if ($.cluster.status.ajax) browse(href);
  else location.href = href;
});

$('#filter-panel .filter').on('click', function () {
  let $this = $(this), active = $this.hasClass('active');
  let ids = $this.attr('id').replace('-', '=').split('=');
  let href = toggleQueryString(ids[0], ids[1], !active);
  if (!$.cluster.status.ajax) return location.href = href;
  postApi(trimUrl(href), {data: {}}, function (res) {
    $.cluster.setChars(res.data.chars);
    $.cluster.updatePager(res.data.pager);
    window.history.pushState({}, null, href);
    $(`.btn-${ids[0]}`).removeClass('active');
    !active && $this.addClass('active');
  });
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
  let ch = $.cluster.status.chars[$(this).attr('data-value')];
  $.cluster.switchCurChar(ch);
  $.charTxt.setChar(ch);
});

// 选中字图
$(document).on('click', '.char-item .char-info, .char-item .char-check', function () {
  $(this).parent().find(':checkbox').click();
});

$(document).on('click', '.char-check input', function (e) {
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
    bsShow('', '保存成功！', 'info', 1000, '#b-alert');
    location.href = setAnchor(char.name);
    // $.charTxt.setBoxLogs(res['box_logs']);
    // $.cluster.status.curChar['box_logs'] = res['box_logs'];
    if (res['img_url']) {  // 已更新字图
      let $img = $('.char-item#' + char.name + ' img');
      if ($img.length) $img.attr('src', res['img_url']);
    }
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
