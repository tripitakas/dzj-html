/*
 * proofread.js
 *
 * Date: 2018-9-19
 */

/*-----------切分字框相关代码----------------*/
var showText = false;                     // 是否显示字框对应文字
var showOrder = false;                    // 是否显示字框对应序号
var showBlockBox = false;                 // 是否显示栏框切分坐标
var showColumnBox = false;                // 是否显示列框切分坐标
var offsetInSpan;                         // 当前选中范围的开始位置
var currentSpan = [null];                 // $(当前span)，是否第一个

function getBlock(blockNo) {
  return $('#sutra-text .block').eq(blockNo - 1);
}

function getLine(blockNo, lineNo) {
  return getBlock(blockNo).find('.line').eq(lineNo - 1);
}

function getBlockNo(block) {
  return $('#sutra-text .block').index(block) + 1;
}

function getLineNo(line) {
  return line.parent().find('.line').index(line) + 1;
}

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
  var $span = $line.find('span');
  $span.each(function (i, el) {
    if ($(el).parent().prop('tagName') !== 'LI') {  // 忽略嵌套span，在新建行中粘贴其他行的内容产生的
      return;
    }
    var text = $(el).text().replace(/[\sYM　]/g, '');  // 正字Y，模糊字M，*不明字占位
    if ($(el).hasClass('variant')) {
      chars = chars.concat(text.split(''));  // chars.push($(el).text());
    } else {
      var mb4Chars = ($(el).attr('utf8mb4') || '').split(',');
      var mb4Map = {}, order = 'a', c;

      mb4Chars.forEach(function (mb4Char) {
        if (mb4Char && text.indexOf(mb4Char) !== -1) {
          mb4Map[order] = mb4Char;
          text = text.replace(new RegExp(mb4Char, 'g'), order);
          order = String.fromCharCode(order.charCodeAt() + 1);
        }
      });

      text = text.split('').map(function (c) {
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
      caretOffset = range.startOffset;               // 获取选定区的开始点
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
  var block_no = getBlockNo($block);
  var line_no = getLineNo($line);
  var offset0 = parseInt($span.attr('offset'));
  offsetInSpan = first ? 0 : getCursorPosition($span[0]);
  var offsetInLine = offsetInSpan + offset0;
  var ocrCursor = ($span.attr('base') || '')[offsetInSpan];
  var cmp1Cursor = ($span.attr('cmp1') || '')[offsetInSpan];
  var text = $span.text().replace(/\s/g, '');
  var i, chTmp, all, cmp_ch;

  // 根据文字序号寻找序号对应的字框
  var boxes = $.cut.findCharsByOffset(block_no, line_no, offsetInLine);

  // 根据文字的栏列号匹配到字框的列，然后根据文字精确匹配列中的字框
  if (boxes.length === 0)
    boxes = $.cut.findCharsByLine(block_no, line_no, function (ch) {
      return ch === ocrCursor || ch === cmp1Cursor;
    });

  // 行内多字能匹配时就取char_no位置最接近的，不亮显整列
  if (boxes.length > 1) {
    boxes[0] = findBestBoxes(offsetInLine, block_no, line_no, function (ch) {
      return ch === ocrCursor || ch === cmp1Cursor;
    }) || boxes[0];
  }

  // 或者用span任意字精确匹配
  if (!boxes.length) {
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

  all = $.cut.findCharsByLine(block_no, line_no);
  $.cut.switchCurrentBox(((boxes.length ? boxes : all)[0] || {}).shape);
}

// 点击切分框
$.cut.onBoxChanged(function (char, box, reason) {
  if (reason === 'navigate' && char) {
    // 按字序号浮动亮显当前行的字框
    var $line = getLine(char.block_no, char.line_no);
    var text = getLineText($line);
    var all = $.cut.findCharsByLine(char.block_no, char.line_no);

    // 如果字框对应的文本行不是当前行，则更新相关设置
    var currentLineNo = getLineNo($('.current-span').parent());
    if (currentLineNo !== char.line_no) {
      var $firstSpan = $line.find('span:first-child');
      currentSpan = [$firstSpan, true];
    }

    $.cut.removeBandNumber(0, true);
    $.cut.showFloatingPanel(
        (showOrder || showText) ? all : [],
        function (char, index) {
          var no = showOrder ? char.char_no : '';
          var txt = !text[index] ? '？' : showText ? text[index] : '';
          // var cc = char.cc || 1;
          // var same = !char.ocr_txt || text[index] === char.ocr_txt || cc < 0.35;
          // return no + txt + (showText ? (same && (cc > 0.5 || cc < 0.35) ? '' : same ? '？' : char.ocr_txt) : '');
          return no + txt;
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
  }
});


/*-----------文本区域相关代码----------------*/

// 设置当前span和line
function setCurrent(span) {
  if (!$('.current-span').is(span)) {
    $('.current-span').removeClass('current-span');
    $(span).addClass('current-span');
    $('.current-line').removeClass('current-line');
    span.parent().addClass('current-line');
  }
}

// 单击同文、异文，设置当前span
$(document).on('click', '.same, .diff', function () {
  setCurrent($(this));
  highlightBox($(this));
});

// 双击异文，弹框提供选择
$(document).on('dblclick', '.diff', function (e) {
  e.stopPropagation();

  setCurrent($(this));

  // 设置当前异文
  $(".current-diff").removeClass('current-diff');
  $(this).addClass('current-diff');

  // 设置弹框文本
  var baseText = $(this).attr("base");
  $("#pfread-dialog-base").text(baseText);
  $("#pfread-dialog-cmp1").text($(this).attr("cmp1"));
  $("#pfread-dialog-cmp2").text($(this).attr("cmp2"));
  $("#pfread-dialog-slct").text($(this).text());
  $("#pfread-dialog-cmp1").toggleClass('same-base', baseText && baseText === $(this).attr("cmp1"));
  $("#pfread-dialog-cmp2").toggleClass('same-base', baseText && baseText === $(this).attr("cmp2"));

  // 设置弹框位置
  var $dlg = $("#pfread-dialog");
  $dlg.show().offset({top: $(this).offset().top + 45, left: $(this).offset().left - 4});

  // 当弹框超出文字框时，向上弹出
  var r_h = $(".pfread .right").height();
  var o_t = $dlg.offset().top;
  var d_h = $('.dialog-abs').height();
  $('.dialog-abs').removeClass('dialog-common-t').addClass('dialog-common');
  if (o_t + d_h > r_h) {
    $dlg.offset({top: $(this).offset().top - 180});
    $('.dialog-abs').removeClass('dialog-common').addClass('dialog-common-t');
  }

  // 设置弹框小箭头
  if (o_t + d_h > r_h) {
    var $mark = $dlg.find('.dlg-after');
    var ml = $mark.attr('last-left') || $mark.css('marginLeft');
    $mark.attr('last-left', ml);
    $mark.css('marginLeft', parseInt(ml) - offset);
  } else {
    $mark = $dlg.find('.dlg-before');
    ml = $mark.attr('last-left') || $mark.css('marginLeft');
    $mark.attr('last-left', ml);
    $mark.css('marginLeft', parseInt(ml) - offset);
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
});

// 粘貼時自動把格式去掉
$(document).on('paste', 'span', function (e) {
  e.preventDefault();
  var text = e.originalEvent.clipboardData.getData('text/plain');
  document.execCommand('insertHTML', false, text);
});

// 单击文本区的空白区域
$('.pfread .right').on('click', function (e) {
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
$('#pfread-dialog .option').on('click', function () {
  $('#pfread-dialog-slct').text($(this).text());
});

$("#pfread-dialog-slct").on('DOMSubtreeModified', function () {
  $('.current-diff').text($(this).text()).addClass('selected');
  if ($(this).text() === '') {
    $('.current-diff').addClass('empty-place');
  } else {
    $('.current-diff').removeClass('empty-place');
  }
});


/*-----------存疑相关代码----------------*/
// 存疑对话框
$('#save-doubt').on('click', function () {
  var txt = window.getSelection ? window.getSelection().toString() : '';
  if (!txt.length || !currentSpan[0]) {
    return showError('请先选择存疑文字', '');
  }
  $('#doubtModal').modal();
  $('#doubtModal .doubt_input').val(txt);
  $('#doubtModal .doubt_reason').val('');
});

// 切换存疑列表
$('.doubt-list .toggle-tab').on('click', function () {
  $(this).addClass('active').siblings().removeClass('active');
  var index = $('.doubt-list .toggle-tab').index($(this));
  $('.doubt-list .char-list-table').removeClass('active').eq(index).addClass('active');
});

// 存疑确认
$('#doubtModal .modal-confirm').on('click', function () {
  var txt = $('#doubtModal .doubt_input').val().trim();
  var reason = $('#doubtModal .doubt_reason').val().trim();
  if (reason.length <= 0)
    return showTips('请填写存疑理由');
  var $span = $('.current-span');
  var offset0 = parseInt($span.attr('offset') || 0);
  var offsetInLine = offsetInSpan + offset0;
  var lineId = $span.parent().attr('id');
  if (!lineId)
    return showTips('请先在文本区内选择文本');
  var line = "<tr class='char-list-tr' data='" + lineId + "' data-offset='" + offsetInLine +
      "'><td>" + lineId.replace(/[^0-9]/g, '') + "</td><td>" + offsetInLine +
      "</td><td>" + txt + "</td><td>" + reason +
      "</td><td class='del-doubt'><img src='/static/imgs/del_icon.png'></td></tr>";

  // 提交之后底部列表自动展开
  $('.doubt-list .toggle-tab').eq(0).click();
  $('.doubt-list .char-list-table.editable').append(line).removeClass('hidden');
  $('#toggle-arrow').removeClass('active');
  $('#doubtModal').modal('hide');
  markChanged();
});

$('#toggle-arrow').on('click', function () {
  $(this).toggleClass('active');
  $('.doubt-list .char-list-table.active').toggleClass('hidden');
});

// 关闭对话框时，清空输入框内容
$('#doubtModal').on('hide.bs.modal', function () {
  $('#doubt_input').val('');
  $('#doubt_reason').val('');
});

// 点击删除按钮，删除该行
$(document).on('click', '.del-doubt', function () {
  $(this).parent().remove();
});

// 记下当前span
$('.line > span').on('mousedown', function () {
  currentSpan[0] = $(this);
});

// 记下选中位置
$('.line > span').on('mouseup', function () {
  offsetInSpan = getCursorPosition(this);
});

function findSpanByOffset($li, offset) {
  var ret = [null, 0];
  $li.find('span').each(function (i, item) {
    var off = parseInt($(item).attr('offset'));
    if (i === 0) {
      ret = [$(this), offset]
    } else if (off <= offset) {
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
$(document).on('click', '.char-list-tr:not(.del-doubt)', function () {
  var $tr = $(this), id = $tr.attr('data'), $li = $('#' + id);
  var pos = findSpanByOffset($li, parseInt($tr.attr('data-offset')));
  var txt = $tr.find('td:nth-child(3)').text();

  // 滚动到文本行
  $('.right .bd .sutra-text').animate({scrollTop: $li.offset().top}, 100);

  // 高亮存疑文本
  if (pos[0]) {
    highlightInSpan(pos[0][0], pos[1], pos[1] + txt.length);
    setCurrent(pos[0]);
  }
});

// 存疑列表的操作按钮
$(document).ready(function () {
  $('table#doubt-table-view tr').find('td:eq(4)').hide();
});

/*------------其它功能---------------*/
var write_back_txt = {};

// 图文匹配
function checkMismatch(report, fromApi) {
  var mismatch = [];
  var lineCountMisMatch = '', ocrColumns = [];

  // 文本区每行的栏号和列号
  var lineNos = $('#sutra-text .line').map(function (i, line) {
    var blockNo = getBlockNo($(line).parent());
    var lineNo = getLineNo($(line));
    return {blockNo: blockNo, lineNo: lineNo};
  }).get();

  if (!fromApi) {
    return updateWideChars(lineNos, function() {
      checkMismatch(report, true);
    });
  }

  // ocrColumns: 从字框提取所有列（栏号和列号）
  $.cut.data.chars.forEach(function (c) {
    if (c.shape && c.line_no) {
      var t = c.block_no + ',' + c.line_no;
      if (ocrColumns.indexOf(t) < 0) {
        ocrColumns.push(t);
      }
    }
  });

  // 先检查行列数是否匹配
  if (lineNos.length !== ocrColumns.length) {
    lineCountMisMatch = '总行数#文本' + lineNos.length + '行#图片' + ocrColumns.length + '行';
    mismatch.splice(0, 0, lineCountMisMatch);
  }
  write_back_txt = {};
  workChanged -= 100000;
  lineNos.forEach(function (no) {
    var boxes = $.cut.findCharsByLine(no.blockNo, no.lineNo);
    var $line = getLine(no.blockNo, no.lineNo);
    var text = getLineText($line);
    var len = text.length;
    $line.toggleClass('mismatch', boxes.length !== len);
    if (boxes.length === len) {
      $line.removeAttr('mismatch');
    } else {
      $line.attr({mismatch: boxes.length + '!=' + len});
    }
    if (boxes.length !== len) {
      mismatch.push('第' + no.lineNo + '行#文本 ' + len + '字#图片' + boxes.length + '字');
    } else {  // 只要字数匹配就回写txt到字框，需要审校者仔细核对每个字
      boxes.forEach(function (c, i) {
        if (text[i].length === 1 && text[i].charCodeAt(0) > 256) {
          write_back_txt[c.char_id] = text[i];
        }
      });
    }
  });
  workChanged += 100000;
  if (report) {
    if (mismatch.length) {
      var text = mismatch.map(function (t) {
        var ts = t.split('#');
        return '<li><span class="head">' + ts[0] + ':</span><span>' + ts[1] + '</span><span>' + ts[2] + '</span></li>';
      }).join('');
      text = '<ul class="tips">' + text + '</ul>';
      showWarning("图文不匹配", text);
    } else {
      showTips("成功", "图文匹配");
    }
  }
}

// 调用后台API，根据文本行内容识别宽字符
function updateWideChars(lineNos, ended) {
  var texts = [];
  lineNos.forEach(function (no) {
    var $line = getLine(no.blockNo, no.lineNo);
    var spans = [];
    texts.push(spans);
    $line.find('span').each(function (i, el) {
      if ($(el).parent().prop('tagName') === 'LI') {  // 忽略嵌套span，在新建行中粘贴其他行的内容产生的
        var text = $(el).text().replace(/[\sYM　]/g, '');  // 正字Y，模糊字M，*不明字占位
        spans.push(text);
      }
    });
  });

  postApi('/task/detect_chars', {data: {texts: texts}}, function(res) {
    lineNos.forEach(function (no, lineIdx) {
      var $line = getLine(no.blockNo, no.lineNo);
      $line.find('span').each(function (i, el) {
        if ($(el).parent().prop('tagName') === 'LI') {
          var mb4 = res.data[lineIdx][i];
          $(el).attr('utf8mb4', mb4);
        }
      });
    });
    ended();
  }, ended);
}

$(document).ready(function () {
  checkMismatch(false);
});

$('#check-match').on('click', function () {
  checkMismatch(true);
});

// 重新比对选择本和OCR
$('#re-compare').on("click", function () {
  showConfirm("确定重新比对吗？", "将使用第一步选择的文本重新比对，并清空当前的校对结果！", function () {
    autoSave(function() {
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


/*-----------导航条----------------*/
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
  if ($curSpan.length === 0) {
    return showError('提示', '请先在右边文本区点击一行文本，然后重试。');
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
  if ($curSpan.length === 0) {
    return showError('提示', '请先在文本区点选一行文本，然后重试。');
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
  if ($curSpan.length === 0) {
    return showError('提示', '请先在文本区点选一行文本，然后重试。');
  }
  var $currentLine = $curSpan.parent(".line");
  $curSpan.removeClass("current-span");
  var newline = "<li class='line'><span contentEditable='true' class='same add current-span'></span></li>";
  $currentLine.after(newline);
});

// 隐藏异体字
$('.btn-variants-highlight').on('click', function () {
  $('.variant').removeClass("variant-highlight");
  $(this).removeClass("btn-variants-highlight");
  $(this).addClass("btn-variants-normal");
});

// 显示异体字
$('.btn-variants-normal').on('click', function () {
  $('.variant').addClass("variant-highlight");
  $(this).removeClass("btn-variants-normal");
  $(this).addClass("btn-variants-highlight");
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
  autoSave(function() {
    location = '/data/cut_edit/' + docId + '?step=chars&from=' + encodeFrom();
  });
});

// 修改栏框
$('#ed-block-box').click(function () {
  autoSave(function() {
    location = '/data/cut_edit/' + docId + '?step=blocks&from=' + encodeFrom();
  });
});

// 修改列框
$('#ed-column-box').click(function () {
  autoSave(function() {
    location = '/data/cut_edit/' + docId + '?step=columns&from=' + encodeFrom();
  });
});

// 修改字序
$('#ed-char-order').click(function () {
  autoSave(function() {
    location = '/data/cut_edit/' + docId + '?step=orders&from=' + encodeFrom();
  });
});

$('#sutra-text').on('DOMSubtreeModified', markChanged);

// 设置改动标记，自动本地缓存
function markChanged() {
  if (workChanged > 0) {
    workChanged++;
  }
}

function autoSave(ended) {
  if (workChanged) {
    saveTask(false, null, function() {
      ended && ended();
    });
  } else {
    ended();
  }
}
