// 显隐字框
$('#toggle-char').on('click', () => $.cut.toggleBox(!$(this).hasClass('active')));

// 显隐浮动列框序号
$('#toggle-panel-no').on('click', function () {
  $(this).toggleClass('active');
  showOrder = $(this).hasClass('active');
  highlightBox();
  setStorage('togglePanelNo', $(this).hasClass('active') ? '1' : '-1');
});

// 显隐浮动面板文本
$('#toggle-panel-txt').on('click', function () {
  $(this).toggleClass('active');
  showText = $(this).hasClass('active');
  highlightBox();
  setStorage('togglePanelTxt', $(this).hasClass('active') ? '1' : '-1');
});

// 增加浮动面板字体
$('#enlarge-panel-font').on('click', function () {
  let $tspan = $('#holder tspan');
  let size = parseInt($tspan.css('font-size'));
  $tspan.css('font-size', ++size + 'px');
  $.cut.data.fontSize = size;
});

// 减少浮动面板字体
$('#reduce-panel-font').on('click', function () {
  let $tspan = $('#holder tspan');
  let size = parseInt($tspan.css('font-size'));
  $tspan.css('font-size', --size + 'px');
  $.cut.data.fontSize = size;
});

// 上一条异文
function previousDiff() {
  let $diff = $('.diff');
  let idx = $diff.index($('.current-diff'));
  if ($diff.eq(idx - 1).length) {
    $diff.eq(idx - 1)[0].scrollIntoView(true);
    $diff.eq(idx - 1).click().dblclick();
  }
}

$('#prev-diff').on('click', previousDiff);
$.mapKey('tab', previousDiff);

// 下一条异文
function nextDiff() {
  let $diff = $('.diff');
  let idx = $diff.index($('.current-diff'));
  if ($diff.eq(idx + 1).length) {
    $diff.eq(idx + 1)[0].scrollIntoView(true);
    $diff.eq(idx + 1).click().dblclick();
  }
}

$('#next-diff').on('click', nextDiff);
$.mapKey('shift+tab', nextDiff);

// 删除当前行
$('#delete-line').on('click', function () {
  let $curSpan = $('.current-span');
  if (!$curSpan.length) {
    return showTips('提示', '请先点击一行文本，然后再删除。', 3000);
  }
  showConfirm('删除', '确定删除当前行吗？', function () {
    let $currentLine = $curSpan.parent(".line");
    $currentLine.fadeOut(500).fadeIn(500);
    setTimeout(function () {
      $currentLine.remove();
    }, 500);
  }, true);
});

// 显示空位符
$('#toggle-empty').on('click', () => $('.empty-place').toggleClass("hide"));

// 缩小图片
$('#zoom-in').on('click', () => highlightBox());

// 放大图片
$('#zoom-out').on('click', () => highlightBox());

// 原始大小
$('#zoom-reset').on('click', () => highlightBox());

// 修改切分
$('#btn-ed-box').on('click', function () {
  autoSave(function () {
    location = '/page/cut_edit/' + docId + '?step=box&from=' + encodeFrom();
  });
});

// 查看切分
$('#btn-vw-box').on('click', function () {
  location = '/page/cut_view/' + docId + '?step=box&from=' + encodeFrom();
});

// 修改字序
$('#btn-ed-order').on('click', function () {
  autoSave(function () {
    location = '/page/cut_edit/' + docId + '?step=order&from=' + encodeFrom();
  });
});

// 查看字序
$('#btn-vw-order').on('click', function () {
  location = '/page/cut_view/' + docId + '?step=order&from=' + encodeFrom();
});

// 修改文本
$('#btn-ed-txt').on('click', function () {
  autoSave(function () {
    location = location.href.replace(/\?.+$/, '') + '?txt_mode=char&step=proof';
  });
});

// 增加字体
$('#enlarge-font').on('click', function () {
  let size = parseInt($('#raw-txt').css('font-size'));
  $('#raw-txt').css('font-size', ++size + 'px');
});

// 减少字体
$('#reduce-font').on('click', function () {
  let size = parseInt($('#raw-txt').css('font-size'));
  $('#raw-txt').css('font-size', --size + 'px');
});