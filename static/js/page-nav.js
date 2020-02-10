/**
 @desc 页面图导航相关操作
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
  var style = $.cut.data.image.node.style;
  style.display = style.display === 'none' ? '' : 'none';
});

// 模糊图片
$(document).on('click', '#toggle-blur', function () {
  $(this).toggleClass('active');
  var style = $.cut.data.image.node.style;
  style.opacity = $(this).hasClass('active') ? 0.2 : 1;
});

function updateThreeButton() {
  var charActive = $('#toggle-char').hasClass('active');
  var blockActive = $('#toggle-block').hasClass('active');
  var columnActive = $('#toggle-column').hasClass('active');
  if (charActive && blockActive && columnActive)
    $('#toggle-three').addClass('active');
  else if (!charActive && !blockActive && !columnActive)
    $('#toggle-three').removeClass('active');
}

// 显隐栏框
$(document).on('click', '#toggle-block', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'block');
  updateThreeButton();
});

// 显隐列框
$(document).on('click', '#toggle-column', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'column');
  updateThreeButton();
});

// 显隐字框
$(document).on('click', '#toggle-char', function () {
  $(this).toggleClass('active');
  $.cut.toggleBox($(this).hasClass('active'), 'char');
  updateThreeButton();
});

// 显隐所有
$(document).on('click', '#toggle-three', function () {
  $(this).toggleClass('active');
  if ($(this).hasClass('active')) {
    $('.toggle-box').addClass('active');
    $.cut.toggleBox(true);
  } else {
    $('.toggle-box').removeClass('active');
    $.cut.toggleBox(false);
  }
});

// 显隐字框编号
$(document).on('click', '#toggle-char-no', function () {
  $(this).toggleClass('active');
  $.cut.toggleLabel();
});

// 显隐字序连线
$(document).on('click', '#toggle-order', function () {
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
