/*
 * tripitaka.js
 *
 * Date: 2019-08-05
 */


// 高度自适应
$(document).ready(function () {
  var h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

$(window).resize(function () {
  var h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

// 收起左侧目录
$('.m-header .toggle-btn').click(function () {
  var $mainLeft = $('.main-left');
  console.log($mainLeft.css('display'));
  localStorage.setItem('toggleTripitaka', $mainLeft.css('display') === 'block' ? 'hide': 'show');
  if ($mainLeft.css('display') == 'block') {
    $mainLeft.hide();
    $('#main-right .m-header').css('left', 0);
  } else {
    $mainLeft.show();
    $('#main-right .m-header').css('left', $mainLeft.width());
  }
});
if (localStorage.getItem('toggleTripitaka') === 'hide') {
  $('.m-header .toggle-btn').click();
}

// 显示、隐藏左侧区域
$('.m-header .zone-control .zone-left').click(function () {
  $('.main-right .content .content-left').toggleClass('hide');
  $('.m-header .m-pager .left').toggleClass('hide');
});

// 显示、隐藏右侧区域
$('.m-header .zone-control .zone-right').click(function () {
  $('.main-right .content .content-right').toggleClass('hide');
  $('.m-header .m-pager .right').toggleClass('hide');
});

// 跳转某一页
$('.m-pager .btn-page:not(.to)').click(function () {
  window.location = '/t/' + $(this).attr("title");
});

// 跳转第n页
$('.m-pager .btn-page.to').on("keydown", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode == "13") {
    jump($('.m-pager .btn-page.to input').val());
  }
});

function jump(page) {
  var cur_volume = $('.m-header #cur-volume').text();
  if (cur_volume && page) {
    window.location = '/t/' + cur_volume + '_' + page;
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

// 查看栏框
$('.show-block-box').click(function () {
  var page_code = $('.m-pager .btn-page.to input').attr('title').trim();
  window.location = '/task/cut_proof/' + page_code + '?step=block_box';
});

// 查看列框
$('.show-column-box').click(function () {
  var page_code = $('.m-pager .btn-page.to input').attr('title').trim();
  window.location = '/task/cut_proof/' + page_code + '?step=column_box';
});

// 查看字框
$('.show-char-box').click(function () {
  var page_code = $('.m-pager .btn-page.to input').attr('title').trim();
  window.location = '/task/cut_proof/' + page_code + '?step=char_box';
});

// 查看字序
$('.show-order-box').click(function () {
  var page_code = $('.m-pager .btn-page.to input').attr('title').trim();
  window.location = '/task/cut_proof/' + page_code + '?step=char_order';
});

// 增加文本字号
$('.m-header').on('click', '.btn-font-enlarge', function () {
  var $div = $('.content-right .page-text');
  var size = parseInt($div.css('font-size'));
  if (size < 36) {
    size++;
    $div.css('font-size', size + 'px');
  }
});

// 减少文本字号
$('.m-header').on('click', '.btn-font-reduce', function () {
  var $div = $('.content-right .page-text');
  var size = parseInt($div.css('font-size'));
  if (size > 8) {
    size--;
    $div.css('font-size', size + 'px');
  }
});

// 展开节点
$('.main-left').on('click', '.has-sub', function () {
  if ($(this).next('.sub-ul').hasClass('sub-ul-hidden')) {
    $('.main-left .sub-ul').addClass('sub-ul-hidden');
    $(this).next('.sub-ul').removeClass('sub-ul-hidden');
  } else {
    $(this).next('.sub-ul').addClass('sub-ul-hidden');
  }
});

// 目录跳转
$('.main-left').on('click', '.leaf', function () {
  window.location = '/t/' + $(this).attr('id');
});

// 检索目录
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

// 检索目录
$('.menu-search-wrapper').on("keydown", ".menu-search-input", function (event) {
  var keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    $(".menu-search-wrapper .menu-search-btn").click();
    event.preventDefault();
  }
});

// 全局经目信息
var sutra_maps = [];
if (typeof (sutras) !== 'undefined') {
  for (var i in sutras) {
    var sutra = sutras[i];
    sutra_maps[sutra[0]] = sutra;
  }
}

function get_sutra_title(tripitaka, sutra_no) {
  sutra_no = sutra_no.toString();
  sutra_no = sutra_no.length < 4 ? sutra_no.padStart(4, "0") : sutra_no;
  var sutra = sutra_maps[tripitaka + sutra_no];
  if (sutra !== undefined) {
    return sutra_no + '.' + sutra[1];
  } else {
    return sutra_no + '.经';
  }
}

// 初始化目录
$(document).ready(function () {
  if (typeof (volumes) === 'undefined' || typeof (store_pattern) === 'undefined') return;
  // 生成目录树
  var tripitaka = location.pathname.match(/\/([A-Z]{2})/)[1];
  var mulu_html = volumes.map(function (item) {
    var id = tripitaka + '_' + item[0];
    var cls = item[1].length ? 'has-sub' : 'leaf';
    var title = '第' + item[0] + store_pattern.split('_')[1];
    if (store_pattern.indexOf('经') !== -1) {
      title = get_sutra_title(tripitaka, item[0]);
    }
    var sub = '';
    if (item[1].length) {
      var _li = item[1].map(function (s) {
        var _id = id + '_' + s;
        var _title = '第' + s + store_pattern.split('_')[2];
        if (/\s/.test(s)) {  // 卷、册允许显示名称
          _id = id + '_' + s.split(' ')[0];
          _title = s.split(' ')[1];
        }
        return '<li><span id="' + _id + '" class="leaf sub-item"><a>' + _title + '</a></span></li>';
      }).join('');
      sub = '<ul class="sub-ul sub-ul-hidden">' + _li + '</ul>';
    }
    return '<li class="menu-item"><span id="' + id + '" class="menu-title ' + cls + '"><a>' + title + '</a></span>' + sub + '</li>';
  }).join('');
  $('#side-menu').html(mulu_html);

  // 选中当前目录
  var cur_menu_id = $('#cur-volume').text().trim();
  $('#' + cur_menu_id).addClass('active');
  $('#' + cur_menu_id).parents('.sub-ul').removeClass('sub-ul-hidden')
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
  data: typeof (sutras) === 'undefined' ? [] : sutras,
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
      'targets': [4],
      'data': 'id',
      'render': function (data, type, full) {
        return '<span class="page-code" title="' + full[4] + '">' + full[4] + '</span>'
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
      'targets': [6],
      'data': 'id',
      'render': function (data, type, full) {
        return '<span class="page-code" title="' + full[6] + '">' + full[6] + '</span>'
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
  window.location = '/t/' + $(this).attr('title');
});
