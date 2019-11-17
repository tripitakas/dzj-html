/*
 * proofread.js
 *
 * Date: 2018-9-19
 */

/*-----------切分字框相关代码----------------*/

var showBlockBox = false;                 // 是否显示栏框切分坐标
var showColumnBox = false;                // 是否显示列框切分坐标
var showOrder = false;                    // 是否显示字框对应序号
var showText = false;                     // 是否显示字框对应文字
var currentSpan = [null];                 // $(当前span)，是否第一个
var offsetInSpan;                         // 当前选中范围的开始位置

function findBestBoxes(offset, block_no, line_no, cmp) {
  var minNo = 10;
  var ret;
  $.cut.findCharsByLine(block_no, line_no, function (ch, box) {
    if (cmp(ch)) {
      if (minNo > Math.abs(offset + 1 - box.char_no)) {
        minNo = Math.abs(offset + 1 - box.char_no);
        ret = box;
      }
    }
  });
}

function getLineText($line) {
  var chars = [];
  $line.find('span').each(function (i, el) {
    if ($(el).hasClass('variant')) {
      chars.push($(el).text());
    } else {
      var text = $(el).text().replace(/\s/g, '');
      var mb4Chars = ($(el).attr('utf8mb4') || '').split(',');
      var mb4Map = {}, order = 'a', c;

      mb4Chars.forEach(function(mb4Char) {
        if (mb4Char && text.indexOf(mb4Char) !== -1) {
          mb4Map[order] = mb4Char;
          text = text.replace(new RegExp(mb4Char, 'g'), order);
          order = String.fromCharCode(order.charCodeAt() + 1);
        }
      });

      text = text.split('').map(function(c) {
        return mb4Map[c] || c;
      });
      chars = chars.concat(text);
    }
  });
  return chars;
}

// 获取当前光标位置、当前选中高亮文本范围在当前span的开始位置
function getCursorPosition(element) {
  var caretOffset = 0;
  var doc = element.ownerDocument || element.document;
  var win = doc.defaultView || doc.parentWindow;
  var sel, range, preCaretRange;

  if (typeof win.getSelection !== 'undefined') {    // 谷歌、火狐
    sel = win.getSelection();
    if (sel.rangeCount > 0) {                       // 选中的区域
      range = sel.getRangeAt(0);
      caretOffset = range.startOffset;            // 获取选定区的开始点
      // preCaretRange = range.cloneRange();         // 克隆一个选中区域
      // preCaretRange.selectNodeContents(element);  // 设置选中区域的节点内容为当前节点
      // preCaretRange.setEnd(range.endContainer, range.endOffset);  // 重置选中区域的结束位置
      // caretOffset = preCaretRange.toString().length;
    }
  } else if ((sel = doc.selection) && sel.type !== 'Control') {    // IE
    range = sel.createRange();                          // 创建选定区域
    preCaretRange = doc.body.createTextRange();
    preCaretRange.moveToElementText(element);
    preCaretRange.setEndPoint('EndToEnd', range);
    caretOffset = preCaretRange.text.length;
  }
  return caretOffset;
}

// 点击文字区域时，高亮文字所对应的字框
function highlightBox($span, first) {
  if (!$span) {
    $span = currentSpan[0];
    first = currentSpan[1];
    if (!$span) {
      return;
    }
  }
  var $line = $span.parent(), $block = $line.parent();
  var block_no = parseInt($block.attr('id').replace(/^.+-/, ''));
  var line_no = parseInt(($line.attr('id') || '').replace(/^.+-/, ''));
  var offset0 = parseInt($span.attr('offset'));
  offsetInSpan = first ? 0 : getCursorPosition($span[0]);
  var offsetInLine = offsetInSpan + offset0;
  var ocrCursor = ($span.attr('base') || '')[offsetInSpan];
  var cmp1Cursor = ($span.attr('cmp1') || '')[offsetInSpan];
  var text = $span.text().replace(/\s/g, '');
  var i, chTmp, all, cmp_ch;

  // 根据文字的栏列号匹配到字框的列，然后根据文字精确匹配列中的字框
  var boxes = $.cut.findCharsByLine(block_no, line_no, function (ch) {
    return ch === ocrCursor || ch === cmp1Cursor;
  });
  // 行内多字能匹配时就取char_no位置最接近的，不亮显整列
  if (boxes.length > 1) {
    boxes[0] = findBestBoxes(offsetInLine, block_no, line_no, function (ch) {
      return ch === ocrCursor || ch === cmp1Cursor;
    }) || boxes[0];
  }
  // 或者用span任意字精确匹配
  else if (!boxes.length) {
    cmp_ch = function (what, ch) {
      return !what || ch === what;
    };
    for (i = 0; i < text.length && !boxes.length; i++) {
      chTmp = cmp_ch.bind(null, text[i]);
      boxes = $.cut.findCharsByLine(block_no, line_no, chTmp);
    }
    if (boxes.length > 1) {
      boxes[0] = findBestBoxes(offsetInLine, block_no, line_no, chTmp) || boxes[0];
    } else if (!boxes.length) {
      boxes = $.cut.findCharsByLine(block_no, line_no, function (ch, box, i) {
        return i === offsetInLine;
      });
    }
  }

  $.cut.removeBandNumber(0, true);
  $.cut.state.focus = false;
  $.fn.mapKey.enabled = false;
  $.cut.data.block_no = block_no;
  $.cut.data.line_no = line_no;
  currentSpan = [$span, first];

  // 按字序号浮动亮显当前行的字框
  text = getLineText($line);
  all = $.cut.findCharsByLine(block_no, line_no);
  $.cut.showFloatingPanel(
      (showOrder || showText) ? all : [],
      function (char, index) {
        return (showOrder ? char.char_no : '') + (!text[index] ? '？' : showText ? text[index] : '');
      },
      highlightBox
  );

  // 显示当前栏框
  if (showBlockBox) {
    $.cut.showBox('blockBox', window.blocks, all.length && all[0].char_id.split('c')[0]);
  }

  // 显示当前列框
  if (showColumnBox) {
    $.cut.showBox('columnBox', window.columns, all.length && all[0].char_id.split('c').slice(0, 2).join('c'));
  }

  $.cut.switchCurrentBox(((boxes.length ? boxes : all)[0] || {}).shape);
}


/*-----------文本区域相关代码----------------*/

// 单击异文，弹框提供选择
$(document).on('click', '.not-same', function (e) {
  e.stopPropagation();

  // 设置当前span
  $('.current-span').attr("contentEditable", "false");
  $('.current-span').removeClass("current-span");
  $(this).addClass('current-span');

  // 设置当前异文
  $(".current-not-same").removeClass('current-not-same');
  $(this).addClass('current-not-same');

  $("#pfread-dialog-base").text($(this).attr("base"));
  $("#pfread-dialog-cmp1").text($(this).attr("cmp1"));
  $("#pfread-dialog-cmp2").text($(this).attr("cmp2"));
  $("#pfread-dialog-slct").text($(this).text());

  var $dlg = $("#pfread-dialog");
  $dlg.offset({top: $(this).offset().top + 45, left: $(this).offset().left - 4}).show();

  //当弹框超出文字框时，向上弹出
  var r_h = $(".right.fr").height();
  var o_t = $dlg.offset().top;
  var d_h = $('.dialog-abs').height();
  var shouldUp = false;
  $('.dialog-abs').removeClass('dialog-common-t').addClass('dialog-common');
  if (o_t + d_h > r_h) {
    $dlg.offset({top: $(this).offset().top - 180});
    $('.dialog-abs').removeClass('dialog-common').addClass('dialog-common-t');
    shouldUp = true;
  }

  // 当弹框右边出界时，向左移动
  var r_w = $dlg.parent()[0].getBoundingClientRect().right;
  var o_l = $dlg.offset().left;
  var d_r = $dlg[0].getBoundingClientRect().right;
  var offset = 0;
  if (d_r > r_w - 20) {
    offset = parseInt(r_w - d_r - 20);
    $dlg.offset({left: o_l + offset});
  }

  var $mark = $dlg.find('.dlg-after');
  var ml = $mark.attr('last-left') || $mark.css('marginLeft');
  if (shouldUp) {
    $mark.attr('last-left', ml);
    $mark.css('marginLeft', parseInt(ml) - offset);
  }

  $mark = $dlg.find('.dlg-before');
  ml = $mark.attr('last-left') || $mark.css('marginLeft');
  if (!shouldUp) {
    $mark.attr('last-left', ml);
    $mark.css('marginLeft', parseInt(ml) - offset);
  }

  // 高亮字框
  highlightBox($(this));

});

// 单击同文，设置当前span
$(document).on('click', '.same', function () {
  $(".current-span").removeClass("current-span");
  $(this).addClass("current-span");
  highlightBox($(this));
});

// 双击同文，设置为可编辑
$(document).on('dblclick', '.same', function () {
  $(".same").attr("contentEditable", "false");
  $(this).attr("contentEditable", "true");
});

// 单击文本区的空白区域
$(document).on('click', '.pfread-in .right', function (e) {
  // 隐藏对话框
  var dlg = $('#pfread-dialog');
  if (!dlg.is(e.target) && dlg.has(e.target).length === 0) {
    dlg.offset({top: 0, left: 0}).hide();
  }
});

// 滚动文本区滚动条
$('.pfread .right').scroll(function () {
  $("#pfread-dialog").offset({top: 0, left: 0}).hide();
});

// 点击异文选择框的各个选项
$(document).on('click', '#pfread-dialog .option', function () {
  $('#pfread-dialog-slct').text($(this).text());
});

$(document).on('DOMSubtreeModified', "#pfread-dialog-slct", function () {
  $('.current-not-same').text($(this).text()).addClass('selected');
  if ($(this).text() === '') {
    $('.current-not-same').addClass('empty-place');
  } else {
    $('.current-not-same').removeClass('empty-place');
  }
});

/*-----------导航条----------------*/

// 缩小画布
$(document).on('click', '.btn-reduce', function () {
  if ($.cut.data.ratio > 0.5) {
    $.cut.setRatio($.cut.data.ratio * 0.9);
    highlightBox();
  }
});

// 放大画布
$(document).on('click', '.btn-enlarge', function () {
  if ($.cut.data.ratio < 5) {
    $.cut.setRatio($.cut.data.ratio * 1.5);
    highlightBox();
  }
});

// 显隐所有字框
window.showAllBoxes = function () {
  var $this = $('.btn-cut-show');
  $this.removeClass("btn-cut-show");
  $this.addClass("btn-cut-hidden");
  $.cut.toggleBox(true);
  $.fn.mapKey.bindings = {up: {}, down: {}};
  $.cut.bindKeys();
};
$(document).on('click', '.btn-cut-show', window.showAllBoxes);
$(document).on('click', '.btn-cut-hidden', function () {
  $(this).removeClass("btn-cut-hidden");
  $(this).addClass("btn-cut-show");
  $.cut.toggleBox(false);
  $.fn.mapKey.bindings = {up: {}, down: {}};
  $.cut.bindMatchingKeys();
});

// 显隐字框对应序号
$(document).on('click', '.btn-num-show', function () {
  $(this).removeClass("btn-num-show");
  $(this).addClass("btn-num-hidden");
  showOrder = !showOrder;
  highlightBox();
  $('#order').toggle(showOrder);
});
$(document).on('click', '.btn-num-hidden', function () {
  $(this).removeClass("btn-num-hidden");
  $(this).addClass("btn-num-show");
  showOrder = !showOrder;
  highlightBox();
  $('#order').toggle(showOrder);
});

// 显隐字框对应文本
$(document).on('click', '.btn-txt-show', function () {
  $(this).removeClass("btn-txt-show");
  $(this).addClass("btn-txt-hidden");
  showText = !showText;
  highlightBox();
});
$(document).on('click', '.btn-txt-hidden', function () {
  $(this).removeClass("btn-txt-hidden");
  $(this).addClass("btn-txt-show");
  showText = !showText;
  highlightBox();
});

// 上一条异文
function previousDiff() {
  var current = $('.current-not-same');
  var $notSame = $('.pfread .right .not-same');
  var idx = $notSame.index(current);
  if (idx < 1) {
    return;
  }
  $notSame.eq(idx - 1).click();
  if ($('.dialog-abs').offset().top < 50) {
    $('.right .bd').animate({scrollTop: $('#pfread-dialog').offset().top + 100}, 500);
  }
}

$(document).on('click', '.btn-previous', previousDiff);
$.mapKey('tab', previousDiff);


// 下一条异文
function nextDiff() {
  var current = $('.current-not-same');
  var $notSame = $('.pfread .right .not-same');
  var idx = $notSame.index(current);
  $notSame.eq(idx + 1).click();
  if ($('.dialog-abs').offset().top + $('.dialog-abs').height() > $('.bd').height()) {
    $('.right .bd').animate({scrollTop: $('#pfread-dialog').offset().top - 100}, 500);
  }
}

$(document).on('click', '.btn-next', nextDiff);
$.mapKey('shift+tab', nextDiff);

// 减少文本字号
$(document).on('click', '.btn-font-reduce', function () {
  var $div = $('.right .sutra-text span');
  var size = parseInt($div.css('font-size'));
  if (size > 8) {
    size--;
    // $('.font-current').text(size);
    $div.css('font-size', size + 'px');
  }
});

// 增加文本字号
$(document).on('click', '.btn-font-enlarge', function () {
  var $div = $('.right .sutra-text span');
  var size = parseInt($div.css('font-size'));
  if (size < 36) {
    size++;
    // $('.font-current').text(size);
    $div.css('font-size', size + 'px');
  }
});

// 删除该行
$(document).on('click', '.btn-delete-line', function () {
  var $curSpan = $('.current-span');
  if ($curSpan.length === 0) {
    return showError('提示', '请先在右边文本区点击一行文本，然后重试。');
  }
  var $currentLine = $curSpan.parent(".line");
  $currentLine.fadeOut(500).fadeIn(500);
  if ($currentLine.text().trim() === '') {
    setTimeout(function () {
      $currentLine.remove()
    }, 1100);
  } else {
    setTimeout(function () {
      $currentLine.addClass('delete')
    }, 1100);
  }
});

// 向上增行
$(document).on('click', '.btn-add-up-line', function (e) {
  e.stopPropagation();
  var $curSpan = $('.current-span');
  if ($curSpan.length === 0) {
    return showError('提示', '请先在文本区点选一行文本，然后重试。');
  }
  var $currentLine = $curSpan.parent(".line");
  $curSpan.removeClass("current-span");
  var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
  $currentLine.before(newline);
});

// 向下增行
$(document).on('click', '.btn-add-down-line', function (e) {
  e.stopPropagation();
  var $curSpan = $('.current-span');
  if ($curSpan.length === 0) {
    return showError('提示', '请先在文本区点选一行文本，然后重试。');
  }
  var $currentLine = $curSpan.parent(".line");
  $curSpan.removeClass("current-span");
  var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
  $currentLine.after(newline);
});

// 隐藏异体字
$(document).on('click', '.btn-variants-highlight', function () {
  $('.variant').removeClass("variant-highlight");
  $(this).removeClass("btn-variants-highlight");
  $(this).addClass("btn-variants-normal");
});

// 显示异体字
$(document).on('click', '.btn-variants-normal', function () {
  $('.variant').addClass("variant-highlight");
  $(this).removeClass("btn-variants-normal");
  $(this).addClass("btn-variants-highlight");
});

// 显示空位符
$(document).on('click', '.btn-empty-places', function () {
  $('.empty-place').toggleClass("hidden");
});

// 弹出原文
$(document).on('click', '.btn-text', function () {
  $('#txtModal').modal();
});

// 检查图文匹配
function checkMismatch(report) {
  var mismatch = [];
  var total = '', ocrColumns = [];
  var lineNos = $('#sutra-text .line').map(function () {
    var blockNo = parseInt($(this).parent().attr('id').replace(/[^0-9]/g, ''));
    var lineNo = parseInt($(this).attr('id').replace(/[^0-9]/g, ''));
    return {blockNo: blockNo, lineNo: lineNo};
  }).get();
  console.log(lineNos.length);

  $.cut.data.chars.forEach(function (c) {
    if (c.shape && c.line_no) {
      var t = c.block_no + ',' + c.line_no;
      if (ocrColumns.indexOf(t) < 0) {
        ocrColumns.push(t);
      }
    }
  });
  total = '总行数#文本' + lineNos.length + '行#图片' + ocrColumns.length + '行';
  lineNos.forEach(function (no) {
    var boxes = $.cut.findCharsByLine(no.blockNo, no.lineNo);
    var $line = $('#block-' + no.blockNo + ' #line-' + no.lineNo);
    var len = getLineText($line).length;
    $line.toggleClass('mismatch', boxes.length !== len);
    if (boxes.length !== len) {
      mismatch.push('第' + no.lineNo + '行#文本 ' + len + '字#图片' + boxes.length + '字');
    }
  });
  if (report) {
    if ((total || mismatch.length)) {
      mismatch.splice(0, 0, total);
      var text = mismatch.map(function (t) {
        var ts = t.split('#');
        return '<li><span class="head">' + ts[0] + ':</span><span>' + ts[1] + '</span><span>' + ts[2] + '</span></li>';
      }).join('');
      text = '<ul class="tips">' + text + '</ul>';
      // text = '<ul class="help tips"><li><span class="head">总行数:</span><span>' + total + '</span></li>' + text + '</ul>';
      swal({title: "图文不匹配", text: text, showConfirmButton: false, allowOutsideClick: true, html: true});
    } else {
      swal({title: "图文匹配", showConfirmButton: false, allowOutsideClick: true, timer: 500});
    }
  }
}

$(document).ready(function () {
  checkMismatch();
});

$(document).on('click', '.btn-check', function () {
  checkMismatch(true);
});

/*-----------存疑相关代码----------------*/

// 存疑对话框
$(document).on('click', '.btn-doubt', function () {
  var word = window.getSelection ? window.getSelection().toString() : null;
  if (word.length <= 0 || !currentSpan[0]) {
    return showError('请先选择存疑文字', '');
  }

  $('#doubtModal').modal();
  $('#doubt_input').val(word);
});

// 切换存疑列表
$(document).on('click', '.tab-editable', function () {
  $(this).siblings().removeClass('active');
  $(this).addClass('active');
  $('#doubt-table-view').addClass('hide');
  $('#doubt-table-editable').removeClass('hide');
});

$(document).on('click', '.tab-view', function () {
  $(this).siblings().removeClass('active');
  $(this).addClass('active');
  $('#doubt-table-editable').addClass('hide');
  $('#doubt-table-view').removeClass('hide');
});

// 存疑提交
$(document).on('click', '#doubt_save_btn', function () {
  var txt = $('#doubt_input').val().trim();
  var reason = $('#doubt_reason').val().trim();
  if (reason.length <= 0) {
    $('#doubt_tip').show();
    return;
  }

  var $span = currentSpan[0];
  var offset0 = parseInt($span.attr('offset'));
  var offsetInLine = offsetInSpan + offset0;
  var lineId = $span.parent().attr('id');
  var line = "<tr class='char-list-tr' data='" + lineId + "' data-offset='" + offsetInLine +
      "'><td>" + lineId.replace(/[^0-9]/g, '') + "</td><td>" + offsetInLine +
      "</td><td>" + txt + "</td><td>" + reason +
      "</td><td class='del-doubt'><img src='/static/imgs/del_icon.png')></td></tr>";
  $('#doubt-table-editable').append(line);
  $('#doubtModal').modal('hide');

  //提交之后底部以列表自动展开
  $('#table_toggle_btn').removeClass('active');
  $('#table_toggle_btn').addClass('');
  $('#doubt-table-editable').addClass('');
  $('#doubt-table-editable').removeClass('hidden');
});

$(document).on('click', '#table_toggle_btn', function () {
  $(this).toggleClass('active');
  $('#doubt-table-editable').toggleClass('hidden');
});

// 关闭对话框时，输入框内容置空
$('#doubtModal').on('hide.bs.modal', function () {
  $('#doubt_input').val('');
  $('#doubt_reason').val('');
  $('#doubt_tip').hide();
});

// 点击删除按钮，删除该行
$(document).on('click', '.del-doubt', function () {
  $(this).parent().remove();
});

// 记下当前span
$(document).on('mousedown', '.line > span', function () {
  currentSpan[0] = $(this);
});

// 记下选中位置
$(document).on('mouseup', '.line > span', function () {
  offsetInSpan = getCursorPosition(this);
});

function findSpanByOffset($li, offset) {
  var ret = [null, 0];
  $li.find('span').each(function () {
    var off = parseInt($(this).attr('offset'));
    if (off <= offset) {
      ret = [$(this), offset - off];
    }
  });
  return ret;
}

function highlightInSpan(startNode, startOffset, endOffset) {
  var text = startNode.innerText;
  $(startNode).html(text.substring(0, startOffset) + '<b style="color: #f00">' +
      text.substring(startOffset, endOffset) + '</b>' + text.substring(endOffset));
  setTimeout(function () {
    $(startNode).text(text);
  }, 1300);
}

// 点击存疑行表格，对应行blink效果
$(document).on('click', '.char-list-tr', function () {
  var $tr = $(this), id = $tr.attr('data'), $li = $('#' + id);
  var pos = findSpanByOffset($li, parseInt($tr.attr('data-offset')));
  var txt = $tr.find('td:nth-child(3)').text();

  $('.right .bd').animate({scrollTop: $li.offset().top + 400}, 100);

  // 闪烁，原字高亮
  if (pos[0]) {
    highlightInSpan(pos[0][0], pos[1], pos[1] + txt.length);
  }
  (pos[0] || $li).addClass('blink');
  setTimeout(function () {
    (pos[0] || $li).removeClass("blink");
  }, 500);
});
