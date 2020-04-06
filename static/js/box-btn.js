/**
 @desc 字框相关操作
 */

// 缩小图片
$(document).on('click', '#zoom-out', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 0.9);
  } else {
    $.cut.setRatio($.cut.data.ratio * 0.9);
  }
});

// 放大图片
$(document).on('click', '#zoom-in', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 1.5);
  } else {
    $.cut.setRatio($.cut.data.ratio * 1.5);
  }
});

// 原始大小
$(document).on('click', '#zoom-reset', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width('100%');
  } else {
    $.cut.setRatio(1);
  }
});

// 显隐图片
$(document).on('click', '#toggle-image', function () {
  $(this).toggleClass('active');
  $.cut.data.image.node.style.display = $(this).hasClass('active') ? '' : 'none';
  var key = $(this).parent().hasClass('order') ? 'toggleOrderImage' : 'toggleImage';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 模糊图片
$(document).on('click', '#toggle-blur', function () {
  $(this).toggleClass('active');
  $.cut.data.image.node.style.opacity = $(this).hasClass('active') ? 0.2 : 1;
  var key = $(this).parent().hasClass('order') ? 'toggleOrderBlur' : 'toggleBlur';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐栏框
$(document).on('click', '#toggle-block', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'block');
  var key = $(this).parent().hasClass('order') ? 'toggleOrderBlock' : 'toggleBlock';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐列框
$(document).on('click', '#toggle-column', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'column');
  var key = $(this).parent().hasClass('order') ? 'toggleOrderColumn' : 'toggleColumn';
  setStorage(key, $(this).hasClass('active') ? '1' : '-1');
});

// 显隐字框
$(document).on('click', '#toggle-char', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'char');
  var key = $(this).parent().hasClass('order') ? 'toggleOrderChar' : 'toggleChar';
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
$(document).on('click', '#toggle-link', function () {
  $(this).toggleClass('active');
  $.cut.setLink($(this).hasClass('active'));
  setStorage('toggleOrder', $(this).hasClass('active') ? '1' : '-1');
});

// 更多操作
$(document).on('click', '#toggle-more', function () {
  $('#more-group').toggleClass('hide');
});
