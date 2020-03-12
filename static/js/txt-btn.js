// 显隐字框
$('#toggle-char').on('click', function () {
  $.cut.toggleBox(!$(this).hasClass('active'));
});

// 显隐浮动列框序号
$('#toggle-panel-no').on('click', function () {
  $(this).toggleClass('active');
  showOrder = $(this).hasClass('active');
  highlightBox();
  localStorage.setItem('togglePanelNo', $(this).hasClass('active') ? '1' : '-1');
});
if (localStorage.getItem('togglePanelNo') === '1') {
  showOrder = true;
  $('#toggle-panel-no').addClass('active');
} else {
  showOrder = false;
  $('#toggle-panel-no').removeClass('active');
}

// 显隐浮动面板的文本
$('#toggle-panel-txt').on('click', function () {
  $(this).toggleClass('active');
  showText = $(this).hasClass('active');
  highlightBox();
  localStorage.setItem('togglePanelTxt', $(this).hasClass('active') ? '1' : '-1');
});
if (localStorage.getItem('togglePanelTxt') !== '-1') {
  showText = true;
  $('#toggle-panel-txt').addClass('active');
} else {
  showText = false;
  $('#toggle-panel-txt').removeClass('active');
}

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
  $diff.eq(idx - 1).click().dblclick();
  if ($('.dialog-abs').offset().top < 55) {
    $('.right #sutra-text').animate({scrollTop: $('.dialog-abs').offset().top - 50}, 300);
    setTimeout(function () {
      $diff.eq(idx - 1).click().dblclick();
    }, 500);
  }
}

$('#prev-diff').on('click', previousDiff);
$.mapKey('tab', previousDiff);

// 下一条异文
function nextDiff() {
  var current = $('.current-diff');
  var $diff = $('.pfread .right .diff');
  var idx = $diff.index(current);
  $diff.eq(idx + 1).click().dblclick();
  if ($('.dialog-abs').offset().top + $('.dialog-abs').height() > $('#sutra-text').height()) {
    $('.right #sutra-text').animate({scrollTop: $('.dialog-abs').offset().top + 50}, 300);
    setTimeout(function () {
      $diff.eq(idx + 1).click().dblclick();
    }, 500);
  }
}

$('#next-diff').on('click', nextDiff);
$.mapKey('shift+tab', nextDiff);

if ($('.pfread .right .diff').length < 1) {
  $('#prev-diff').remove();
  $('#next-diff').remove();
}

// 删除当前行
$('#delete-line').on('click', function () {
  var $curSpan = $('.current-span');
  if (!$curSpan.length) {
    return showError('提示', '请先点击一行文本，然后再删除。');
  }
  showConfirm('删除', '确定删除当前行吗？', function () {
    var $currentLine = $curSpan.parent(".line");
    $currentLine.fadeOut(500).fadeIn(500);
    setTimeout(function () {
      $currentLine.remove();
    }, 500);
  }, true);
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

// 修改切分
$('#btn-ed-box').click(function () {
  autoSave(function () {
    location = '/page/cut_edit/' + docId + '?step=box&from=' + encodeFrom();
  });
});

// 查看切分
$('#btn-vw-box').click(function () {
  location = '/page/cut_view/' + docId + '?step=box&from=' + encodeFrom();
});


// 修改字序
$('#btn-ed-order').click(function () {
  autoSave(function () {
    location = '/page/cut_edit/' + docId + '?step=order&from=' + encodeFrom();
  });
});

// 查看字序
$('#btn-vw-order').click(function () {
  location = '/page/cut_view/' + docId + '?step=order&from=' + encodeFrom();
});

// 修改文本
$('#btn-ed-txt').click(function () {
  autoSave(function () {
    location = location.href.replace(/\?.+$/, '') + '?txt_mode=char&step=proof';
  });
});

$('#ed-char-std').click(function () {
  autoSave(function () {
    location = location.href.replace(/\?.+$/, '');
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
