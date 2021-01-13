/*
 * tripitaka.js
 *
 * Date: 2019-08-05
 */


// 高度自适应
$(document).ready(function () {
  let h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

$(window).resize(function () {
  let h = $(document.body).height();
  $('#main-left').height(h);
  $('#main-right').height(h);
});

// 显隐左侧目录
$(document).on('click', '#toggle-menu', function () {
  let $menu = $('#left-menu');
  $menu.toggleClass('hide');
  if ($menu.hasClass('hide')) {
    $('#main-right .m-header').css('left', 0);
  } else {
    $('#main-right .m-header').css('left', $menu.width());
  }
  localStorage.setItem('toggleMenu', $menu.hasClass('hide') ? 'hide' : 'show');
});
if (localStorage.getItem('toggleMenu') === 'hide') {
  $('#toggle-menu').click();
}

// 显隐右侧区域
$('#toggle-text').on('click', function () {
  $('#right-region').toggleClass('hide');
  localStorage.setItem('toggleText', $('#right-region').hasClass('hide') ? 'hide' : 'show');
});
if (localStorage.getItem('toggleText') === 'hide') {
  $('#right-region').addClass('hide');
}

// 跳转某一页
$('.m-pager .btn-page:not(.to)').on('click', function () {
  window.location = '/tripitaka/' + $(this).attr("title");
});

// 跳转第n页
$('.m-pager .btn-page.to').on("keydown", function (event) {
  let keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    jump($('.m-pager .btn-page.to input').val());
  }
});

function jump(page) {
  let curVolume = $('#cur-volume').text();
  if (curVolume && page) {
    window.location = '/tripitaka/' + curVolume + '_' + page;
  }
}

// 切换文本
$('#txtModal .btn-txt').on('click', function () {
  $(this).removeClass('btn-default').addClass('btn-primary');
  $(this).siblings().removeClass('btn-primary').addClass('btn-default');
  let txtType = $(this).attr('id').replace('show-', '');
  if (txtType === 'all')
    $('#txtModal textarea').show();
  else
    $('#txtModal #' + txtType).show().siblings().hide();
});

// 图片向左翻页
$('#pic-left').on('click', function () {
  $('.btn-page.prev').click();
});

// 图片向右翻页
$('#pic-right').on('click', function () {
  $('.btn-page.next').click();
});

// 快捷键左右翻页
$.mapKey('shift+left', function () {
  $('.m-pager .prev').click();
});

$.mapKey('shift+right', function () {
  $('.m-pager .next').click();
});


// 增加文本字号
$(document).on('click', '#enlarge-font', function () {
  let $div = $('.content-right .page-text');
  let size = parseInt($div.css('font-size'));
  if (size < 36) {
    size++;
    $div.css('font-size', size + 'px');
  }
});

// 减少文本字号
$(document).on('click', '#reduce-font', function () {
  let $div = $('.content-right .page-text');
  let size = parseInt($div.css('font-size'));
  if (size > 8) {
    size--;
    $div.css('font-size', size + 'px');
  }
});

// 展开子节点
$('.main-left').on('click', '.has-sub', function () {
  $(this).next('.sub-ul').toggleClass('sub-ul-hidden');
});

// 目录跳转
$('.main-left').on('click', '.leaf', function () {
  window.location = '/tripitaka/' + $(this).attr('id');
});

// 回车检索
$('.menu-search-wrapper').on("keydown", ".menu-search-input", function (event) {
  let keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    $(".menu-search-wrapper .menu-search-btn").click();
    event.preventDefault();
  }
});

// 检索目录
$(".menu-search-wrapper").on('click', '.menu-search-btn', function () {
  $("#side-menu .sub-ul").addClass('sub-ul-hidden');
  let inputval = new RegExp($(".menu-search-wrapper .menu-search-input").val().trim(), "i");
  let selections = $("#side-menu").find('.menu-item');
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
  let keyCode = event.keyCode || event.which;
  if (keyCode === 13) {
    $(".menu-search-wrapper .menu-search-btn").click();
    event.preventDefault();
  }
});

// 全局经目信息
let sutra_maps = [];
if (typeof (sutras) !== 'undefined') {
  for (let i in sutras) {
    let sutra = sutras[i];
    sutra_maps[sutra[0]] = sutra;
  }
}

function get_sutra_title(tripitaka, sutra_no) {
  sutra_no = sutra_no.toString();
  sutra_no = sutra_no.length < 4 ? sutra_no.padStart(4, "0") : sutra_no;
  let sutra = sutra_maps[tripitaka + sutra_no];
  if (sutra !== undefined) {
    return sutra_no + '.' + sutra[1];
  } else {
    return sutra_no + '.经';
  }
}

// 初始化目录
$(document).ready(function () {
  if (typeof (window.volumes) === 'undefined' || typeof (window.store_pattern) === 'undefined') return;
  // 生成目录树
  let tripitaka = location.pathname.match(/\/([A-Z]{2})/)[1];
  let muluHtml = volumes.map(function (item) {
    let id = tripitaka + '_' + item[0];
    let cls = item[1].length ? 'has-sub' : 'leaf';
    let title = '第' + item[0] + store_pattern.split('_')[1];
    if (store_pattern.indexOf('经') !== -1) {
      title = get_sutra_title(tripitaka, item[0]);
    }
    let sub = '';
    if (item[1].length) {
      let _li = item[1].map(function (s) {
        let _id = id + '_' + s;
        let _title = '第' + s + store_pattern.split('_')[2];
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
  $('#side-menu').html(muluHtml);

  // 选中当前目录
  let curMenuId = $('#cur-volume').text().trim();
  $('#' + curMenuId).addClass('active').parents('.sub-ul').removeClass('sub-ul-hidden');
});

// Datatable本地化
let language = {
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
        let start_page = full[4] + '_' + full[5];
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
        let start_page = full[4] + '_' + full[5];
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
        let end_page = full[6] + '_' + full[7];
        return '<span class="page-code" title="' + end_page + '">' + full[7] + '</span>'
      }
    }
  ]
});

$('#my-sutra-table').on("click", '.page-code', function (event) {
  $('#sutraNavModal').modal('hide');
  window.location = '/tripitaka/' + $(this).attr('title');
});
