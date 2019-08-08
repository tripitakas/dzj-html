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
  // 选中当前目录
  var cur_menu_id = $('#parent-id').text().trim();
  $('#' + cur_menu_id).addClass('active');
  $('#' + cur_menu_id).parents('.sub-ul').removeClass('sub-ul-hidden')
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
  $('.m-header .m-pager .left').toggleClass('hide');
});

// 显示、隐藏右侧区域
$('.m-header .zone-control .zone-right').click(function () {
  $('.main-right .content .content-right').toggleClass('hide');
  $('.m-header .m-pager .right').toggleClass('hide');
});

// 跳转第一页
$('.m-pager .btn-page.first').click(function () {
  window.location = '/t/' + $('.m-header #parent-id').text() + '_' + $(this).attr("title");
});

// 跳转某一页
$('.m-pager .btn-page').click(function () {
  jump($(this).attr("title"));
});

// 跳转第n页
$('.m-pager .btn-page.to').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode == "13") {
    jump($('.m-pager .btn-page.to input').val());
  }
});

function jump(page) {
  var parent_id = $('.m-header #parent-id').text();
  if (parent_id && page) {
    window.location = '/t/' + parent_id.replace(/_/g, '/') + '_' + page;
  }
}

// 缩小图片
$('.m-header').on('click', '.btn-reduce', function () {
  var width = $('.page-picture img').width();
  if (width) {
    $('.page-picture img').width(width * 0.9);
  } else {
    $.cut.setRatio($.cut.data.ratio * 0.9);
  }
});

// 放大图片
$('.m-header').on('click', '.btn-enlarge', function () {
  var width = $('.page-picture img').width();
  if (width) {
    $('.page-picture img').width(width * 1.1);
  } else {
    $.cut.setRatio($.cut.data.ratio * 1.5);
  }
});

// 原始大小
$('.m-header').on('click', '.btn-origin', function () {
  var width = $('.page-picture img').width();
  if (width) {
    $('.page-picture img').width('100%');
  } else {
    $.cut.setRatio(1);
  }
});

// 更多操作
$('.m-header .btn-ed-box').click(function () {
  $('.more-group').toggleClass('hidden');
});

$('.main-left').on('click', '.has-sub', function () {
  $(this).next('.sub-ul').toggleClass('sub-ul-hidden');
});

$('.main-left').on('click', '.leaf', function () {
  var m = $(this).attr('id').match(/([a-zA-Z]{1,2})0*([_0-9]+)/);
  var url = '/t/' + m[1] + '/' + m[2].replace(/^_/, '');
  window.location = url;
});

$(".menu-search-wrapper").on('click', '.menu-search-btn', function () {
  $("#side-menu .sub-ul").addClass('sub-ul-hidden');
  var inputval = new RegExp($(".menu-search-wrapper .menu-search-input").val().trim(), "i");
  var selections = $("#side-menu").find('.menu-item');
  selections.each(function () {
    if ($(this).text().match(inputval)) {
      $(this).show();
    } else {
      $(this).hide();
    }
  })
});

$('.menu-search-wrapper').on("keydown", ".menu-search-input", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    $(".menu-search-wrapper .menu-search-btn").click();
    event.preventDefault();
  }
});


// Datatable本地化
var language = {
  "sProcessing": "处理中...",
  "sLengthMenu": "显示 _MENU_ 项结果",
  "sZeroRecords": "没有匹配结果",
  "sInfo": "显示第 _START_ 至 _END_ 项结果，共 _TOTAL_ 项",
  "sInfoEmpty": "显示第 0 至 0 项结果，共 0 项",
  "sInfoFiltered": "(由 _MAX_ 项结果过滤)",
  "sInfoPostFix": "",
  "sSearch": "搜索:",
  "sUrl": "",
  "sEmptyTable": "表中数据为空",
  "sLoadingRecords": "载入中...",
  "sInfoThousands": ",",
  "oPaginate": {
    "sFirst": "首页",
    "sPrevious": "上页",
    "sNext": "下页",
    "sLast": "末页"
  },
  "oAria": {
    "sSortAscending": ": 以升序排列此列",
    "sSortDescending": ": 以降序排列此列"
  }
};

$('#my-sutra-table').DataTable({
  language: language,
  data: typeof(sutras) === 'undefined' ? [] : sutras,
  columnDefs: [
    {
      'targets': [0],
      'data': 'id',
      'render': function (data, type, full) {
        var start_page = full[4] + '_' + full[5];
        return '<span class="sutra-code page-code" title="' + start_page + '">' + full[0] + '</span>'
      }
    },
    {
      'targets': [5],
      'data': 'id',
      'render': function (data, type, full) {
        var start_page = full[4] + '_' + full[5];
        return '<span class="page-code" title="' + start_page + '">' + full[5] + '</span>'
      }
    },
    {
      'targets': [7],
      'data': 'id',
      'render': function (data, type, full) {
        var end_page = full[6] + '_' + full[7];
        return '<span class="page-code" title="' + end_page + '">' + full[7] + '</span>'
      }
    }
  ]
});

$('#my-sutra-table').on("click", '.page-code', function (event) {
  $('#sutraNavModal').modal('hide');
  var tripitaka = $('.m-header #parent-id').text().split('_')[0];
  window.location = '/t/' + tripitaka + '/' + $(this).attr('title');
});