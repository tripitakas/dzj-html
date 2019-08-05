/*
 * tripitaka.js
 *
 * Date: 2019-08-05
 */


$(document).ready(function () {
  // 高度自适应
  var h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

$(window).resize(function () {
  // 高度自适应
  var h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

// 收起左侧目录
$('.m-header .toggle-btn').click(function () {
  var $mainLeft = $('.main-left');
  console.log($mainLeft.css('display'));
  if ($mainLeft.css('display') == 'block') {
    $mainLeft.hide();
    $('#main-right .m-header').css('left', 0);
  } else {
    $mainLeft.show();
    $('#main-right .m-header').css('left', $mainLeft.width());
  }
});

// 显示、隐藏区域
$('.m-header .zone-control .zone-left').click(function () {
  $('.main-right .content .content-left').toggleClass('hide');
  $('.m-header .sub-line .left').toggleClass('hide');
});

// 显示、隐藏右侧区域
$('.m-header .zone-control .zone-right').click(function () {
  $('.main-right .content .content-right').toggleClass('hide');
  $('.m-header .sub-line .right').toggleClass('hide');
});

// 更多操作
$('.btn-ed-box').click(function () {
  $('.more-group').toggleClass('hidden');
});

// 缩小图片
$(document).on('click', '.btn-reduce', function () {
  var width = $('.page-picture img').width();
  $('.page-picture img').width(width * 0.9);
});

// 放大图片
$(document).on('click', '.btn-enlarge', function () {
  var width = $('.page-picture img').width();
  $('.page-picture img').width(width * 1.1);
});

// 原始大小
$(document).on('click', '.btn-origin', function () {
  $('.page-picture img').width('100%');
});