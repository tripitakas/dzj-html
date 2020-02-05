/**
 @desc 导航相关操作。需提前设置好$.cut。
*/

// 显隐左侧区域
$(document).on('click', '#toggle-left', function () {
  $(this).toggleClass('active');
  $('#left-region').toggleClass('hide');
});

// 隐藏右侧区域
$(document).on('click', '#toggle-right', function () {
  $(this).toggleClass('active');
  $('#right-region').toggleClass('hide');
});

// 图片缩放快捷键
function zoomRatio(ratio) {
  var pageImg = $('#page-picture img');
  if (pageImg.length) {
    pageImg.width((100 * ratio) + '%');
  } else {
    $.cut.setRatio(ratio);
  }
}

$.mapKey('1', function () {
  zoomRatio(1);
});
$.mapKey('2', function () {
  zoomRatio(2);
});
$.mapKey('3', function () {
  zoomRatio(3);
});
$.mapKey('4', function () {
  zoomRatio(4);
});
$.mapKey('5', function () {
  zoomRatio(5);
});
$.mapKey('6', function () {
  zoomRatio(0.6);
});
$.mapKey('7', function () {
  zoomRatio(0.8);
});
$.mapKey('8', function () {
  zoomRatio(0.8);
});
$.mapKey('9', function () {
  zoomRatio(0.9);
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

// 显隐图片
$('#toggle-image').click(function () {
  $(this).toggleClass('active');
  var style = $.cut.data.image.node.style;
  style.display = style.display === 'none' ? '' : 'none';
});

// 模糊图片
$('#toggle-blur').click(function () {
  $(this).toggleClass('active');
  var style = $.cut.data.image.node.style;
  style.opacity = $(this).hasClass('active') ? 0.2 : 1;
});

// 显隐栏框
$('#toggle-block').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleBox('hide', 'block');
});

// 显隐列框
$('#toggle-column').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleBox('hide', 'column');
  // $.cut.toggleColumns(columns);
});

// 显隐字框
$('#toggle-char').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleBox('hide', 'char');
});

// 显隐字框编号
$('#toggle-char-no').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleLabel();
});

// 显隐字序连线
$('#toggle-order').click(function () {
  $(this).toggleClass('active');
  $.cut.toggleLink();
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
