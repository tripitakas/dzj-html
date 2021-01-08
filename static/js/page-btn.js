/**
 @desc 页面图导航相关操作
 */

// 显隐左侧区域
$(document).on('click', '#toggle-left', function () {
  $(this).toggleClass('active');
  $('#left-region').toggleClass('hide', $(this).hasClass('active'));
});

// 隐藏右侧区域
$(document).on('click', '#toggle-right', function () {
  $(this).toggleClass('active');
  $('#right-region').toggleClass('hide', !$(this).hasClass('active'));
});

// 显隐图片
$(document).on('click', '#toggle-image', function () {
  $(this).toggleClass('active');
  if ($.cut.data.image) {
    $.cut.data.image.node.style.display = $(this).hasClass('active') ? '' : 'none';
    let key = $(this).parent().hasClass('order') ? 'toggleOrderImage' : 'toggleImage';
    setStorage(key, $(this).hasClass('active') ? '1' : '-1');
  } else {
    $('.page-img img').toggleClass('hide', !$(this).hasClass('active'));
  }
});

// 模糊图片
$(document).on('click', '#toggle-blur', function () {
  $(this).toggleClass('active');
  if ($.cut.data.image) {
    $.cut.data.image.node.style.opacity = $(this).hasClass('active') ? 0.2 : 1;
    let key = $(this).parent().hasClass('order') ? 'toggleOrderBlur' : 'toggleBlur';
    setStorage(key, $(this).hasClass('active') ? '1' : '-1');
  } else {
    let opacity = $('.page-img img').css('opacity') == '0.2' ? 1 : 0.2;
    $('.page-img img').css('opacity', opacity);
  }

});

// 缩小图片
$(document).on('click', '#zoom-out', function () {
  let pageImg = $('.page-img img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 0.9);
    pageImg.height(pageImg.height() * 0.9);
  } else {
    $.cut.setRatio($.cut.data.ratio * 0.9);
  }
});

// 放大图片
$(document).on('click', '#zoom-in', function () {
  let pageImg = $('.page-img img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 1.5);
    pageImg.height(pageImg.height() * 1.5);
  } else {
    $.cut.setRatio($.cut.data.ratio * 1.5);
  }
});

// 原始大小
$(document).on('click', '#zoom-reset', function () {
  let pageImg = $('.page-img img');
  let ratio = pageImg.width() / pageImg.height();
  if (pageImg.length) {
    pageImg.height('100%');
    pageImg.width(pageImg.height() * ratio);
  } else {
    $.cut.setRatio(1);
  }
});

// 显隐栏框
$(document).on('click', '#toggle-block', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'block');
  let key = $(this).parent().hasClass('order') ? 'toggleOrderBlock' : 'toggleBlock';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐列框
$(document).on('click', '#toggle-column', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'column');
  let key = $(this).parent().hasClass('order') ? 'toggleOrderColumn' : 'toggleColumn';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐字框
$(document).on('click', '#toggle-char', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'char');
  let key = $(this).parent().hasClass('order') ? 'toggleOrderChar' : 'toggleChar';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐所有
$(document).on('click', '#toggle-three', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'));
  $('#toggle-char').toggleClass('active', $(this).hasClass('active'));
  $('#toggle-column').toggleClass('active', $(this).hasClass('active'));
  $('#toggle-block').toggleClass('active', $(this).hasClass('active'));
});

// 显隐字框编号
$(document).on('click', '#toggle-char-no', function () {
  $(this).toggleClass('active');
  $.cut.setLabel($(this).hasClass('active'));
  setStorage('toggleCharNo', $(this).hasClass('active') ? '1' : '-1');
});

// 显隐字序连线
$(document).on('click', '#toggle-order', function () {
  $(this).toggleClass('active');
  $.cut.setLink($(this).hasClass('active'));
  setStorage('toggleOrder', $(this).hasClass('active') ? '1' : '-1');
});

// 更多操作
$(document).on('click', '#toggle-more', function () {
  $('#more-group').toggleClass('hide');
});

// 减少文本字号
$(document).on('click', '#reduce-font', function () {
  let $div = $('.sutra-text span');
  let size = parseInt($div.css('font-size'));
  if (size > 8) {
    size--;
    $div.css('font-size', size + 'px');
  }
});

// 增加文本字号
$(document).on('click', '#enlarge-font', function () {
  let $div = $('.sutra-text span');
  let size = parseInt($div.css('font-size'));
  if (size < 36) {
    size++;
    $div.css('font-size', size + 'px');
  }
});

// 查看page页面
$(document).on('click', '.m-footer .page-name', function () {
  if ($(this).hasClass('disabled'))
    return;
  let url = '/tptk/' + $(this).text();
  let charName = $('.m-footer .char-name').text();
  if (typeof charName !== 'undefined' && charName !== '' && charName !== '未选中') {
    let cid = charName.split('_').pop();
    cid = cid.split('#').pop();
    url += '?cid=' + cid;
  }
  window.open(url, '_blank');
});

// 查看char页面
$(document).on('click', '.m-footer .char-name', function () {
  let charName = $(this).text();
  if ($(this).hasClass('disabled') || charName === '未选中')
    return;
  if (!/b\dc\d+c\d+/.test(charName))
    return showTips('提示', '当前不是字框，无法查看', 3000);
  if (charName.indexOf('#') > -1) {
    let cid = charName.split('#').pop();
    let pageName = $('.m-footer .page-name').text();
    charName = pageName + '_' + cid;
  }
  window.open('/char/' + charName, '_blank');
});

