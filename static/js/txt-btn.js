// 显隐字框
$('#toggle-char').on('click', () => $.cut.toggleBox(!$(this).hasClass('active')));

// 显隐浮动列框序号
$('#toggle-panel-no').on('click', function () {
  $(this).toggleClass('active');
  showOrder = $(this).hasClass('active');
  highlightBox();
  setStorage('togglePanelNo', $(this).hasClass('active') ? '1' : '-1');
});
showOrder = getStorage('togglePanelNo') === '1';
$('#toggle-panel-no').toggleClass('active', getStorage('togglePanelNo') === '1');

// 显隐浮动面板的文本
$('#toggle-panel-txt').on('click', function () {
  $(this).toggleClass('active');
  showText = $(this).hasClass('active');
  highlightBox();
  setStorage('togglePanelTxt', $(this).hasClass('active') ? '1' : '-1');
});
showText = getStorage('togglePanelTxt') === '1';
$('#toggle-panel-txt').toggleClass('active', getStorage('togglePanelTxt') === '1');

// 增加浮动面板的字体
$('#enlarge-panel-font').on('click', function () {
  var $tspan = $('#holder tspan');
  var size = parseInt($tspan.css('font-size'));
  $tspan.css('font-size', ++size + 'px');
  $.cut.data.fontSize = size;
});

// 减少浮动面板的字体
$('#reduce-panel-font').on('click', function () {
  var $tspan = $('#holder tspan');
  var size = parseInt($tspan.css('font-size'));
  $tspan.css('font-size', --size + 'px');
  $.cut.data.fontSize = size;
});

// 上一条异文
function previousDiff() {
  var $diff = $('.diff');
  var idx = $diff.index($('.current-diff'));
  if (idx < 1)
    return;
  $diff.eq(idx - 1).click().dblclick();
  if ($('.dialog-abs').offset().top < 55) {
    $('#sutra-text').animate({scrollTop: $('.dialog-abs').offset().top - 50}, 300);
    setTimeout(() => $diff.eq(idx - 1).click().dblclick(), 500);
  }
}

$('#prev-diff').on('click', previousDiff);
$.mapKey('tab', previousDiff);

// 下一条异文
function nextDiff() {
  var $diff = $('.diff');
  var idx = $diff.index($('.current-diff'));
  $diff.eq(idx + 1).click().dblclick();
  if ($('.dialog-abs').offset().top + $('.dialog-abs').height() > $('#sutra-text').height()) {
    $('.right #sutra-text').animate({scrollTop: $('.dialog-abs').offset().top + 50}, 300);
    setTimeout(() => $diff.eq(idx + 1).click().dblclick(), 500);
  }
}

$('#next-diff').on('click', nextDiff);
$.mapKey('shift+tab', nextDiff);

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

// 显示空位符
$('#toggle-empty').on('click', () => $('.empty-place').toggleClass("hidden"));

// 弹出原文
$('#toggle-txts').on('click', () => $('#txtModal').modal());

// 缩小图片
$('#zoom-in').on('click', () => highlightBox());

// 放大图片
$('#zoom-out').on('click', () => highlightBox());

// 原始大小
$('#zoom-reset').on('click', () => highlightBox());

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
