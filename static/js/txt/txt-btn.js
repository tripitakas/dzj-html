// 显隐字框
$('#toggle-char').on('click', function () {
  $.cut.toggleBox(!$(this).hasClass('active'));
});

// 显隐浮动列框序号
$('#toggle-panel-no').on('click', function () {
  $(this).toggleClass('active');
  showOrder = $(this).hasClass('active');
  highlightBox();
});

// 显隐浮动面板的文本
$('#toggle-panel-txt').on('click', function () {
  $(this).toggleClass('active');
  showText = $(this).hasClass('active');
  highlightBox();
});

// 增加浮动面板的字体
$('#enlarge-panel-font').on('click', function () {
  var $tspan = $('#holder tspan');
  var size = parseInt($tspan.css('font-size'));
  if (size < 36) {
    $tspan.css('font-size', ++size + 'px');
  }
  $.cut.data.fontSize = size;
});

// 减少浮动面板的字体
$('#reduce-panel-font').on('click', function () {
  var $tspan = $('#holder tspan');
  var size = parseInt($tspan.css('font-size'));
  if (size > 8) {
    $tspan.css('font-size', --size + 'px');
  }
  $.cut.data.fontSize = size;
});

// 上一条异文
function previousDiff() {
  var current = $('.current-diff');
  var $diff = $('.pfread .right .diff');
  var idx = $diff.index(current);
  if (idx < 1)
    return;

  $diff.eq(idx - 1).click();
  $diff.eq(idx - 1).dblclick();
  if ($('.dialog-abs').offset().top < 50) {
    $('.right .bd').animate({scrollTop: $('#pfread-dialog').offset().top + 100}, 500);
  }
}

$('#previous-diff').on('click', previousDiff);
$.mapKey('tab', previousDiff);

// 下一条异文
function nextDiff() {
  var current = $('.current-diff');
  var $diff = $('.pfread .right .diff');
  var idx = $diff.index(current);
  $diff.eq(idx + 1).click();
  $diff.eq(idx + 1).dblclick();
  if ($('.dialog-abs').offset().top + $('.dialog-abs').height() > $('.bd').height()) {
    $('.right .bd').animate({scrollTop: $('#pfread-dialog').offset().top - 100}, 500);
  }
}

$('#next-diff').on('click', nextDiff);
$.mapKey('shift+tab', nextDiff);

if ($('.pfread .right .diff').length < 1) {
  $('#previous-diff').remove();
  $('#next-diff').remove();
}

// 删除当前行
$('#delete-line').on('click', function () {
  var $curSpan = $('.current-span');
  if (!$curSpan.length) {
    return showError('请点击文本行', '请先点击一行文本，然后删除。');
  }
  var $currentLine = $curSpan.parent(".line");
  $currentLine.fadeOut(500).fadeIn(500);
  setTimeout(function () {
    $currentLine.remove();
  }, 500);
});

// 向上增行
$('#add-up-line').on('click', function (e) {
  e.stopPropagation();
  var $curSpan = $('.current-span');
  if (!$curSpan.length) {
    return showError('请点击文本行', '请先点击一行文本，然后删除。');
  }
  var $currentLine = $curSpan.parent(".line");
  $curSpan.removeClass("current-span");
  var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
  $currentLine.before(newline);
});

// 向下增行
$('#add-down-line').on('click', function (e) {
  e.stopPropagation();
  var $curSpan = $('.current-span');
  if (!$curSpan.length) {
    return showError('请点击文本行', '请先点击一行文本，然后删除。');
  }
  var $currentLine = $curSpan.parent(".line");
  $curSpan.removeClass("current-span");
  var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
  $currentLine.after(newline);
});

// 隐藏异体字
$('.btn-variants-highlight').on('click', function () {
  $('.variant').removeClass("variant-highlight");
  $(this).removeClass("btn-variants-highlight").addClass("btn-variants-normal");
});

// 显示异体字
$('.btn-variants-normal').on('click', function () {
  $('.variant').addClass("variant-highlight");
  $(this).removeClass("btn-variants-normal").addClass("btn-variants-highlight");
});

// 显示空位符
$('#toggle-empty-place').on('click', function () {
  $('.empty-place').toggleClass("hidden");
});

// 弹出原文
$('#toggle-txts').on('click', function () {
  $('#txtModal').modal();
});

// 缩小图片
$('#zoom-in').on('click', function () {
  highlightBox();
});

// 放大图片
$('#zoom-out').on('click', function () {
  highlightBox();
});

// 图片原始大小
$('#zoom-reset').on('click', function () {
  highlightBox();
});

// 修改字框
$('#ed-char-box').click(function () {
  autoSave(function () {
    location = '/data/cut_edit/' + docId + '?step=box&from=' + encodeFrom();
  });
});

// 修改字序
$('#ed-char-order').click(function () {
  autoSave(function () {
    location = '/data/cut_edit/' + docId + '?step=order&from=' + encodeFrom();
  });
});

// 重新比对选择本和OCR
$('#re-compare').on("click", function () {
  showConfirm("确定重新比对吗？", "将使用第一步选择的文本重新比对，并清空当前的校对结果！", function () {
    autoSave(function () {
      window.location = setQueryString('re_compare', 'true');
    });
  });
});

// 弹出的文本可以拖拽
$('#txtModal .modal-header').on('mousedown', function (downEvt) {
  var $txtModel = $('#txtModal');
  var dragging = false, downX = downEvt.pageX, downY = downEvt.pageY;
  var x = downEvt.pageX - $txtModel.offset().left;
  var y = downEvt.pageY - $txtModel.offset().top;
  $('body').on('mousemove.draggable', function (moveEvt) {
    dragging = dragging || Math.hypot(moveEvt.pageX - downX, moveEvt.pageY - downY) > 10;
    if (dragging) {
      $txtModel.offset({
        left: moveEvt.pageX - x,
        top: moveEvt.pageY - y
      });
    }
  });
  $('body').one('mouseup', function () {
    $('body').off('mousemove.draggable');
  });
  $(this).closest('.modal').one('bs.modal.hide', function () {
    $('body').off('mousemove.draggable');
  });
});

// 切换弹出文本
$('#txtModal .btn-txt').click(function () {
  $(this).removeClass('btn-default').addClass('btn-primary');
  $(this).siblings().removeClass('btn-primary').addClass('btn-default');
  var txtType = $(this).attr('id').replace('show-', '');
  if (txtType === 'all')
    $('#txtModal textarea').removeClass('hide');
  else
    $('#txtModal #' + txtType).removeClass('hide').siblings().addClass('hide');
});

// 增加字体
$('#enlarge-font').click(function () {
  var size = parseInt($('#raw-txt').css('font-size'));
  if (size < 36) {
    size++;
    $('#raw-txt').css('font-size', size + 'px');
  }
});

// 减少字体
$('#reduce-font').click(function () {
  var size = parseInt($('#raw-txt').css('font-size'));
  if (size > 8) {
    size--;
    $('#raw-txt').css('font-size', size + 'px');
  }
});