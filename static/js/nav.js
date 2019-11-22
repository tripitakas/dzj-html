/*
 @desc 导航相关操作
*/

// 显隐左侧区域
$(document).on('click', '#toggle-left', function () {
  $('#left-region').toggleClass('hide');
});

// 隐藏右侧区域
$(document).on('click', '#toggle-right', function () {
  $('#right-region').toggleClass('hide');
});

// 缩小图片
$(document).on('click', '#zoom-in', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 0.9);
  } else {
    $.cut.setRatio($.cut.data.ratio * 0.9);
  }
});

// 放大图片
$(document).on('click', '#zoom-out', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width(pageImg.width() * 1.5);
  } else {
    $.cut.setRatio($.cut.data.ratio * 1.5);
  }
});

// 图片原始大小
$(document).on('click', '#zoom-reset', function () {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width('100%');
  } else {
    $.cut.setRatio(1);
  }
});

// 显隐画布
$(document).on('click', '#toggle-image', function () {
  $(this).toggleClass('active');
  var style = $.cut.data.image.node.style;
  style.display = style.display === 'none' ? '' : 'none';
});

// 更多操作
$(document).on('click', '#toggle-more', function () {
  $('#more-group').toggleClass('hidden');
});

// 减少文本字号
$(document).on('click', '#reduce-font', function () {
  var $div = $('.sutra-text span');
  var size = parseInt($div.css('font-size'));
  if (size > 8) {
    size--;
    $div.css('font-size', size + 'px');
  }
});

// 增加文本字号
$(document).on('click', '#enlarge-font', function () {
  var $div = $('.sutra-text span');
  var size = parseInt($div.css('font-size'));
  if (size < 36) {
    size++;
    $div.css('font-size', size + 'px');
  }
});
